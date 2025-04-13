#!/usr/bin/env python3
"""
GA4 Direct Access

A simple, reliable tool to directly access Garage Assistant 4 data.
This script:
1. Scans the GA4 installation directory for data files
2. Provides a simple web interface to browse the data
3. Works with real data only - no sample data
"""

import os
import sys
import csv
import sqlite3
import logging
import webbrowser
from pathlib import Path
from flask import Flask, jsonify, request, render_template, send_file
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('GA4DirectAccess')

# Add console handler to ensure logs are printed
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)

logger.debug('Starting GA4 Direct Access Tool')

# Default paths
GA4_PATH = r'/Users/adamrutstein/Library/CloudStorage/GoogleDrive-adam@elimotors.co.uk/My Drive'
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ga4_direct.db')

class GA4DirectAccess:
    """Direct access to Garage Assistant 4 data files"""

    def __init__(self, ga4_path=GA4_PATH, db_path=SQLITE_DB_PATH):
        """Initialize the GA4 direct access tool"""
        self.ga4_path = ga4_path
        self.db_path = db_path
        self.connection = None
        self.cursor = None
        self.data_files = []

        # Initialize database
        self._init_database()

        # Scan for GA4 data files
        self._scan_ga4_files()

    def _init_database(self):
        """Initialize the SQLite database"""
        try:
            # Connect to SQLite database
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.cursor = self.connection.cursor()

            # Create metadata table
            self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS ga4_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE,
                file_name TEXT,
                file_size INTEGER,
                last_modified INTEGER,
                imported INTEGER DEFAULT 0
            )
            """)

            self.connection.commit()
            logger.info(f"Initialized SQLite database at {self.db_path}")

            return True

        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False

    def _scan_ga4_files(self):
        """Scan for GA4 data files"""
        try:
            # Check if GA4 path exists
            if not os.path.exists(self.ga4_path):
                logger.error(f"GA4 path not found: {self.ga4_path}")
                return

            # Scan for data files
            data_files = []

            # Look for Data Exports folder
            data_exports_path = os.path.join(self.ga4_path, 'Data Exports')
            if os.path.exists(data_exports_path):
                logger.info(f"Found Data Exports folder at {data_exports_path}")

                # Look for CSV files in Data Exports folder
                for file in os.listdir(data_exports_path):
                    if file.endswith('.csv'):
                        file_path = os.path.join(data_exports_path, file)
                        file_stat = os.stat(file_path)

                        data_files.append({
                            'file_path': file_path,
                            'file_name': file,
                            'file_size': file_stat.st_size,
                            'last_modified': file_stat.st_mtime
                        })
            else:
                logger.warning(f"Data Exports folder not found at {data_exports_path}")

            # Look for CSV files in exports directory
            exports_dir = os.path.join(self.ga4_path, 'exports')
            if os.path.exists(exports_dir):
                for file in os.listdir(exports_dir):
                    if file.endswith('.csv'):
                        file_path = os.path.join(exports_dir, file)
                        file_stat = os.stat(file_path)

                        data_files.append({
                            'file_path': file_path,
                            'file_name': file,
                            'file_size': file_stat.st_size,
                            'last_modified': file_stat.st_mtime
                        })

            # Store data files in database
            for file_info in data_files:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO ga4_files (file_path, file_name, file_size, last_modified) VALUES (?, ?, ?, ?)",
                    (file_info['file_path'], file_info['file_name'], file_info['file_size'], file_info['last_modified'])
                )

            self.connection.commit()

            # Store data files list
            self.data_files = data_files

            logger.info(f"Found {len(data_files)} GA4 data files")

            return True

        except Exception as e:
            logger.error(f"Error scanning GA4 files: {e}")
            return False

    def get_data_files(self):
        """Get list of GA4 data files"""
        try:
            self.cursor.execute("SELECT * FROM ga4_files ORDER BY file_name")
            files = []

            for row in self.cursor.fetchall():
                files.append({
                    'id': row['id'],
                    'file_path': row['file_path'],
                    'file_name': row['file_name'],
                    'file_size': row['file_size'],
                    'last_modified': row['last_modified'],
                    'imported': row['imported']
                })

            return files

        except Exception as e:
            logger.error(f"Error getting data files: {e}")
            return []

    def import_csv_file(self, file_id):
        """Import a CSV file into the database"""
        try:
            # Get file info
            self.cursor.execute("SELECT * FROM ga4_files WHERE id = ?", (file_id,))
            file_info = self.cursor.fetchone()

            if not file_info:
                logger.error(f"File not found: {file_id}")
                return False

            file_path = file_info['file_path']

            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False

            # Check if file is CSV
            if not file_path.endswith('.csv'):
                logger.error(f"Not a CSV file: {file_path}")
                return False

            # Get table name from file name
            table_name = os.path.splitext(file_info['file_name'])[0]
            table_name = ''.join(c if c.isalnum() else '_' for c in table_name)

            # Read CSV file
            with open(file_path, 'r', newline='', encoding='utf-8-sig') as f:
                csv_reader = csv.reader(f)
                headers = next(csv_reader)

                # Clean header names
                headers = [''.join(c if c.isalnum() else '_' for c in header) for header in headers]

                # Create table
                columns = [f"{header} TEXT" for header in headers]
                create_table_query = f"CREATE TABLE IF NOT EXISTS [{table_name}] ({', '.join(columns)})"
                self.cursor.execute(create_table_query)

                # Clear existing data
                self.cursor.execute(f"DELETE FROM [{table_name}]")

                # Insert data
                insert_query = f"INSERT INTO [{table_name}] ({', '.join(['[' + h + ']' for h in headers])}) VALUES ({', '.join(['?' for _ in headers])})"

                record_count = 0
                for row in csv_reader:
                    # Pad row if needed
                    if len(row) < len(headers):
                        row = row + [''] * (len(headers) - len(row))
                    # Truncate row if needed
                    elif len(row) > len(headers):
                        row = row[:len(headers)]

                    self.cursor.execute(insert_query, row)
                    record_count += 1

                # Commit changes
                self.connection.commit()

                # Update file status
                self.cursor.execute("UPDATE ga4_files SET imported = 1 WHERE id = ?", (file_id,))
                self.connection.commit()

                logger.info(f"Imported {record_count} records from {file_info['file_name']} into table {table_name}")

                return True

        except Exception as e:
            logger.error(f"Error importing CSV file: {e}")
            return False

    def get_tables(self):
        """Get list of tables in the database"""
        try:
            # Create a new cursor for this operation to avoid recursive cursor issues
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            tables = [row['name'] for row in cursor.fetchall()]
            cursor.close()
            return tables

        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []

    def get_table_data(self, table_name, page=0, page_size=100):
        """Get data from a table"""
        try:
            # Create a new cursor for this operation to avoid recursive cursor issues
            cursor = self.connection.cursor()

            # Get total count
            cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            total_count = cursor.fetchone()[0]

            # Get column names
            cursor.execute(f"PRAGMA table_info([{table_name}])")
            columns = [row['name'] for row in cursor.fetchall()]

            # Get data with pagination
            offset = page * page_size
            cursor.execute(f"SELECT * FROM [{table_name}] LIMIT {page_size} OFFSET {offset}")

            rows = []
            for row in cursor.fetchall():
                rows.append(dict(row))

            cursor.close()

            return {
                'columns': columns,
                'rows': rows,
                'total_count': total_count,
                'page': page,
                'page_size': page_size
            }

        except Exception as e:
            logger.error(f"Error getting data from table {table_name}: {e}")
            return {
                'columns': [],
                'rows': [],
                'total_count': 0,
                'page': page,
                'page_size': page_size
            }

    def search_database(self, search_term):
        """Search across all tables for a term"""
        results = []
        try:
            # Create a new cursor for this operation to avoid recursive cursor issues
            cursor = self.connection.cursor()

            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            tables = [row['name'] for row in cursor.fetchall()]

            for table in tables:
                # Get table schema
                cursor.execute(f"PRAGMA table_info([{table}])")
                columns = [row['name'] for row in cursor.fetchall()]

                # Build WHERE clause
                where_clauses = []
                for column in columns:
                    where_clauses.append(f"[{column}] LIKE ?")

                # Execute search query
                if where_clauses:
                    query = f"SELECT * FROM [{table}] WHERE {' OR '.join(where_clauses)} LIMIT 100"
                    params = [f'%{search_term}%'] * len(where_clauses)

                    cursor.execute(query, params)

                    for row in cursor.fetchall():
                        record = dict(row)
                        record['_table'] = table
                        results.append(record)

            cursor.close()
            return results

        except Exception as e:
            logger.error(f"Error searching database: {e}")
            return []

    def download_file(self, file_id):
        """Get file path for download"""
        try:
            self.cursor.execute("SELECT file_path FROM ga4_files WHERE id = ?", (file_id,))
            file_info = self.cursor.fetchone()

            if not file_info:
                logger.error(f"File not found: {file_id}")
                return None

            file_path = file_info['file_path']

            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            return file_path

        except Exception as e:
            logger.error(f"Error getting file path: {e}")
            return None

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

# Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Initialize GA4 direct access
ga4 = GA4DirectAccess()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('direct_access.html')

@app.route('/api/files')
def get_files():
    """API endpoint to get list of GA4 data files"""
    return jsonify(ga4.get_data_files())

@app.route('/api/import/<int:file_id>', methods=['POST'])
def import_file(file_id):
    """API endpoint to import a CSV file"""
    success = ga4.import_csv_file(file_id)

    if success:
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to import file'}), 400

@app.route('/api/tables')
def get_tables():
    """API endpoint to get list of tables"""
    return jsonify(ga4.get_tables())

@app.route('/api/table/<table_name>')
def get_table_data(table_name):
    """API endpoint to get data from a table"""
    page = request.args.get('page', 0, type=int)
    page_size = request.args.get('page_size', 100, type=int)

    data = ga4.get_table_data(table_name, page, page_size)

    return jsonify(data)

@app.route('/api/search')
def search_database():
    """API endpoint to search across all tables"""
    search_term = request.args.get('term', '')

    if not search_term:
        return jsonify([])

    results = ga4.search_database(search_term)
    return jsonify(results)

@app.route('/api/download/<int:file_id>')
def download_file(file_id):
    """API endpoint to download a GA4 data file"""
    file_path = ga4.download_file(file_id)

    if not file_path:
        return jsonify({'error': 'File not found'}), 404

    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(templates_dir, exist_ok=True)

    # Create direct_access.html template if it doesn't exist
    template_path = os.path.join(templates_dir, 'direct_access.html')

    if not os.path.exists(template_path):
        with open(template_path, 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GA4 Direct Access</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; }
        .card { margin-bottom: 20px; }
        .table-responsive { max-height: 400px; overflow-y: auto; }
        .nav-tabs { margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">GA4 Direct Access</h1>

        <ul class="nav nav-tabs" id="mainTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="files-tab" data-bs-toggle="tab" data-bs-target="#files" type="button" role="tab">GA4 Files</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="tables-tab" data-bs-toggle="tab" data-bs-target="#tables" type="button" role="tab">Database Tables</button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="search-tab" data-bs-toggle="tab" data-bs-target="#search" type="button" role="tab">Search</button>
            </li>
        </ul>

        <div class="tab-content" id="mainTabsContent">
            <!-- Files Tab -->
            <div class="tab-pane fade show active" id="files" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">GA4 Data Files</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped" id="filesTable">
                                <thead>
                                    <tr>
                                        <th>File Name</th>
                                        <th>Size</th>
                                        <th>Last Modified</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody id="filesTableBody"></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Tables Tab -->
            <div class="tab-pane fade" id="tables" role="tabpanel">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <h5 class="mb-0">Database Tables</h5>
                        <select id="tableSelector" class="form-select" style="width: auto;"></select>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped" id="tableData">
                                <thead id="tableDataHeader"></thead>
                                <tbody id="tableDataBody"></tbody>
                            </table>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mt-3">
                            <div>
                                <span id="tableInfo"></span>
                            </div>
                            <div>
                                <button id="prevPage" class="btn btn-sm btn-outline-primary">Previous</button>
                                <button id="nextPage" class="btn btn-sm btn-outline-primary">Next</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Search Tab -->
            <div class="tab-pane fade" id="search" role="tabpanel">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Search Database</h5>
                    </div>
                    <div class="card-body">
                        <div class="input-group mb-3">
                            <input type="text" id="searchInput" class="form-control" placeholder="Enter search term...">
                            <button id="searchButton" class="btn btn-primary">Search</button>
                        </div>
                        <div id="searchResults"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Global variables
        let currentTable = '';
        let currentPage = 0;
        let pageSize = 100;
        let totalRecords = 0;

        // Load files on page load
        document.addEventListener('DOMContentLoaded', function() {
            loadFiles();
            loadTables();

            // Set up event listeners
            document.getElementById('tableSelector').addEventListener('change', function() {
                currentTable = this.value;
                currentPage = 0;
                loadTableData();
            });

            document.getElementById('prevPage').addEventListener('click', function() {
                if (currentPage > 0) {
                    currentPage--;
                    loadTableData();
                }
            });

            document.getElementById('nextPage').addEventListener('click', function() {
                if ((currentPage + 1) * pageSize < totalRecords) {
                    currentPage++;
                    loadTableData();
                }
            });

            document.getElementById('searchButton').addEventListener('click', function() {
                const searchTerm = document.getElementById('searchInput').value.trim();
                if (searchTerm) {
                    searchDatabase(searchTerm);
                }
            });

            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const searchTerm = this.value.trim();
                    if (searchTerm) {
                        searchDatabase(searchTerm);
                    }
                }
            });
        });

        // Load GA4 data files
        function loadFiles() {
            fetch('/api/files')
                .then(response => response.json())
                .then(files => {
                    const tbody = document.getElementById('filesTableBody');
                    tbody.innerHTML = '';

                    files.forEach(file => {
                        const tr = document.createElement('tr');

                        // Format file size
                        const fileSize = formatFileSize(file.file_size);

                        // Format last modified date
                        const lastModified = new Date(file.last_modified * 1000).toLocaleString();

                        tr.innerHTML = `
                            <td>${file.file_name}</td>
                            <td>${fileSize}</td>
                            <td>${lastModified}</td>
                            <td>
                                <a href="/api/download/${file.id}" class="btn btn-sm btn-outline-primary">Download</a>
                                ${file.file_name.endsWith('.csv') ?
                                    `<button class="btn btn-sm btn-outline-success import-btn" data-id="${file.id}">Import</button>` :
                                    ''}
                            </td>
                        `;

                        tbody.appendChild(tr);
                    });

                    // Add event listeners to import buttons
                    document.querySelectorAll('.import-btn').forEach(btn => {
                        btn.addEventListener('click', function() {
                            const fileId = this.getAttribute('data-id');
                            importFile(fileId);
                        });
                    });
                })
                .catch(error => console.error('Error loading files:', error));
        }

        // Import a CSV file
        function importFile(fileId) {
            fetch(`/api/import/${fileId}`, { method: 'POST' })
                .then(response => response.json())
                .then(result => {
                    if (result.status === 'success') {
                        alert('File imported successfully');
                        loadTables();
                    } else {
                        alert('Failed to import file: ' + (result.message || 'Unknown error'));
                    }
                })
                .catch(error => console.error('Error importing file:', error));
        }

        // Load database tables
        function loadTables() {
            fetch('/api/tables')
                .then(response => response.json())
                .then(tables => {
                    const selector = document.getElementById('tableSelector');
                    selector.innerHTML = '<option value="">Select a table</option>';

                    tables.forEach(table => {
                        const option = document.createElement('option');
                        option.value = table;
                        option.textContent = table;
                        selector.appendChild(option);
                    });

                    // If there are tables, select the first one
                    if (tables.length > 0) {
                        currentTable = tables[0];
                        selector.value = currentTable;
                        loadTableData();
                    }
                })
                .catch(error => console.error('Error loading tables:', error));
        }

        // Load table data
        function loadTableData() {
            if (!currentTable) return;

            fetch(`/api/table/${currentTable}?page=${currentPage}&page_size=${pageSize}`)
                .then(response => response.json())
                .then(result => {
                    const headerRow = document.getElementById('tableDataHeader');
                    const tbody = document.getElementById('tableDataBody');
                    const tableInfo = document.getElementById('tableInfo');

                    headerRow.innerHTML = '';
                    tbody.innerHTML = '';

                    // Update total records
                    totalRecords = result.total_count;

                    // Update table info
                    const start = currentPage * pageSize + 1;
                    const end = Math.min((currentPage + 1) * pageSize, totalRecords);
                    tableInfo.textContent = `Showing ${start} to ${end} of ${totalRecords} records`;

                    // Update prev/next buttons
                    document.getElementById('prevPage').disabled = currentPage === 0;
                    document.getElementById('nextPage').disabled = end >= totalRecords;

                    if (result.rows.length === 0) {
                        headerRow.innerHTML = '<tr><th>No data available</th></tr>';
                        return;
                    }

                    // Create header row
                    const tr = document.createElement('tr');
                    result.columns.forEach(key => {
                        const th = document.createElement('th');
                        th.textContent = key;
                        tr.appendChild(th);
                    });
                    headerRow.appendChild(tr);

                    // Create data rows
                    result.rows.forEach(record => {
                        const tr = document.createElement('tr');
                        Object.values(record).forEach(value => {
                            const td = document.createElement('td');
                            td.textContent = value;
                            tr.appendChild(td);
                        });
                        tbody.appendChild(tr);
                    });
                })
                .catch(error => console.error('Error loading table data:', error));
        }

        // Search database
        function searchDatabase(searchTerm) {
            fetch(`/api/search?term=${encodeURIComponent(searchTerm)}`)
                .then(response => response.json())
                .then(results => {
                    const resultsDiv = document.getElementById('searchResults');
                    resultsDiv.innerHTML = '';

                    if (results.length === 0) {
                        resultsDiv.innerHTML = '<div class="alert alert-info">No results found</div>';
                        return;
                    }

                    // Group results by table
                    const tableGroups = {};
                    results.forEach(record => {
                        const tableName = record._table;
                        if (!tableGroups[tableName]) {
                            tableGroups[tableName] = [];
                        }
                        tableGroups[tableName].push(record);
                    });

                    // Display results by table
                    Object.keys(tableGroups).forEach(tableName => {
                        const records = tableGroups[tableName];

                        // Create table header
                        const tableDiv = document.createElement('div');
                        tableDiv.className = 'mb-4';

                        const tableHeader = document.createElement('h4');
                        tableHeader.textContent = tableName;
                        tableDiv.appendChild(tableHeader);

                        // Create table
                        const table = document.createElement('table');
                        table.className = 'table table-striped table-bordered';

                        // Create header row
                        const thead = document.createElement('thead');
                        const headerRow = document.createElement('tr');

                        // Get all column names from the first record
                        const columns = Object.keys(records[0]).filter(key => key !== '_table');

                        columns.forEach(column => {
                            const th = document.createElement('th');
                            th.textContent = column;
                            headerRow.appendChild(th);
                        });

                        thead.appendChild(headerRow);
                        table.appendChild(thead);

                        // Create table body
                        const tbody = document.createElement('tbody');

                        records.forEach(record => {
                            const row = document.createElement('tr');

                            columns.forEach(column => {
                                const td = document.createElement('td');
                                td.textContent = record[column] || '';
                                row.appendChild(td);
                            });

                            tbody.appendChild(row);
                        });

                        table.appendChild(tbody);
                        tableDiv.appendChild(table);
                        resultsDiv.appendChild(tableDiv);
                    });
                })
                .catch(error => {
                    console.error('Error searching database:', error);
                    document.getElementById('searchResults').innerHTML =
                        '<div class="alert alert-danger">Error searching database</div>';
                });
        }

        // Format file size
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';

            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));

            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    </script>
</body>
</html>''')

    # Run the Flask app
    logger.info("Starting GA4 Direct Access on http://localhost:8080")

    # Open browser automatically
    webbrowser.open('http://localhost:8080')

    app.run(debug=True, host='127.0.0.1', port=8080)
