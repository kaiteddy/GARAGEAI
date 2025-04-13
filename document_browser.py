#!/usr/bin/env python3
"""
GA4 Document Browser

This module provides functionality to browse and connect documents, line items, 
vehicles, and customers from GA4 exports.
"""

import os
import sys
import csv
import sqlite3
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('DocumentBrowser')

# Database path
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'garage_system.db')

def initialize_document_tables():
    """Initialize document-related tables in the database"""
    if not os.path.exists(os.path.dirname(DB_PATH)):
        os.makedirs(os.path.dirname(DB_PATH))
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create documents table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ga4_id TEXT,
        document_number TEXT,
        document_type TEXT,
        document_date TEXT,
        customer_id INTEGER,
        vehicle_id INTEGER,
        total_amount REAL,
        tax_amount REAL,
        status TEXT,
        notes TEXT,
        created_at TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles (id)
    )
    ''')
    
    # Create line_items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS line_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ga4_id TEXT,
        document_id INTEGER,
        description TEXT,
        quantity REAL,
        unit_price REAL,
        total_price REAL,
        tax_rate REAL,
        tax_amount REAL,
        item_type TEXT,
        part_number TEXT,
        labor_hours REAL,
        FOREIGN KEY (document_id) REFERENCES documents (id)
    )
    ''')
    
    # Create document_extras table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS document_extras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER,
        field_name TEXT,
        field_value TEXT,
        FOREIGN KEY (document_id) REFERENCES documents (id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    logger.info("Initialized document-related tables in the database")

def import_documents():
    """Import documents from GA4 exports"""
    ga4_path = r"C:\GA4 User Data"
    exports_path = os.path.join(ga4_path, "Data Exports")
    
    if not os.path.exists(exports_path):
        logger.error(f"GA4 exports path not found: {exports_path}")
        return False
    
    documents_file = os.path.join(exports_path, "Documents.csv")
    line_items_file = os.path.join(exports_path, "LineItems.csv")
    document_extras_file = os.path.join(exports_path, "Document_Extras.csv")
    
    if not os.path.exists(documents_file):
        logger.error(f"Documents file not found: {documents_file}")
        return False
    
    # Initialize database tables
    initialize_document_tables()
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM line_items")
    cursor.execute("DELETE FROM document_extras")
    cursor.execute("DELETE FROM documents")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('documents', 'line_items', 'document_extras')")
    conn.commit()
    
    # Import documents
    try:
        logger.info(f"Importing documents from {documents_file}")
        
        with open(documents_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            
            # Find relevant columns
            ga4_id_col = headers.index('_ID') if '_ID' in headers else -1
            customer_id_col = headers.index('_ID_Customer') if '_ID_Customer' in headers else -1
            vehicle_id_col = headers.index('_ID_Vehicle') if '_ID_Vehicle' in headers else -1
            
            # Look for document number, type, date, and amount columns
            doc_number_col = -1
            doc_type_col = -1
            doc_date_col = -1
            total_amount_col = -1
            tax_amount_col = -1
            status_col = -1
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'number' in header_lower or 'no' in header_lower:
                    doc_number_col = i
                elif 'type' in header_lower:
                    doc_type_col = i
                elif 'date' in header_lower:
                    doc_date_col = i
                elif 'total' in header_lower and ('amount' in header_lower or 'price' in header_lower):
                    total_amount_col = i
                elif 'tax' in header_lower and ('amount' in header_lower or 'price' in header_lower):
                    tax_amount_col = i
                elif 'status' in header_lower:
                    status_col = i
            
            # Get customer and vehicle mappings
            cursor.execute("SELECT id, name FROM customers")
            customers = cursor.fetchall()
            customer_map = {customer[1]: customer[0] for customer in customers}
            
            cursor.execute("SELECT id, registration FROM vehicles")
            vehicles = cursor.fetchall()
            vehicle_map = {vehicle[1]: vehicle[0] for vehicle in vehicles}
            
            # Process documents
            documents_imported = 0
            ga4_id_to_db_id = {}  # Map GA4 IDs to database IDs
            
            for row in reader:
                try:
                    # Skip empty rows
                    if not row or len(row) < 3:
                        continue
                    
                    # Extract document data
                    document_data = {}
                    
                    # Get GA4 ID
                    if ga4_id_col >= 0 and ga4_id_col < len(row):
                        ga4_id = row[ga4_id_col].strip()
                        if ga4_id:
                            document_data['ga4_id'] = ga4_id
                    
                    # Skip if no GA4 ID
                    if 'ga4_id' not in document_data:
                        continue
                    
                    # Get document number
                    if doc_number_col >= 0 and doc_number_col < len(row):
                        doc_number = row[doc_number_col].strip()
                        if doc_number:
                            document_data['document_number'] = doc_number
                    
                    # Get document type
                    if doc_type_col >= 0 and doc_type_col < len(row):
                        doc_type = row[doc_type_col].strip()
                        if doc_type:
                            document_data['document_type'] = doc_type
                    
                    # Get document date
                    if doc_date_col >= 0 and doc_date_col < len(row):
                        doc_date = row[doc_date_col].strip()
                        if doc_date:
                            # Try to parse date
                            try:
                                # Try different date formats
                                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y']:
                                    try:
                                        date_obj = datetime.strptime(doc_date, fmt)
                                        document_data['document_date'] = date_obj.strftime('%Y-%m-%d')
                                        break
                                    except ValueError:
                                        continue
                            except Exception:
                                # If date parsing fails, use as is
                                document_data['document_date'] = doc_date
                    
                    # Get total amount
                    if total_amount_col >= 0 and total_amount_col < len(row):
                        total_amount = row[total_amount_col].strip()
                        if total_amount:
                            try:
                                document_data['total_amount'] = float(total_amount.replace(',', ''))
                            except ValueError:
                                pass
                    
                    # Get tax amount
                    if tax_amount_col >= 0 and tax_amount_col < len(row):
                        tax_amount = row[tax_amount_col].strip()
                        if tax_amount:
                            try:
                                document_data['tax_amount'] = float(tax_amount.replace(',', ''))
                            except ValueError:
                                pass
                    
                    # Get status
                    if status_col >= 0 and status_col < len(row):
                        status = row[status_col].strip()
                        if status:
                            document_data['status'] = status
                    
                    # Get customer ID
                    if customer_id_col >= 0 and customer_id_col < len(row):
                        customer_ga4_id = row[customer_id_col].strip()
                        if customer_ga4_id:
                            # Try to find customer by name in the row
                            for i, header in enumerate(headers):
                                if 'customer' in header.lower() and 'name' in header.lower() and i < len(row):
                                    customer_name = row[i].strip()
                                    if customer_name and customer_name in customer_map:
                                        document_data['customer_id'] = customer_map[customer_name]
                                        break
                    
                    # Get vehicle ID
                    if vehicle_id_col >= 0 and vehicle_id_col < len(row):
                        vehicle_ga4_id = row[vehicle_id_col].strip()
                        if vehicle_ga4_id:
                            # Try to find vehicle by registration in the row
                            for i, header in enumerate(headers):
                                if 'registration' in header.lower() or 'reg' in header.lower() and i < len(row):
                                    registration = row[i].strip().upper().replace(' ', '')
                                    if registration and registration in vehicle_map:
                                        document_data['vehicle_id'] = vehicle_map[registration]
                                        break
                    
                    # Set created_at
                    document_data['created_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Insert document
                    fields = ', '.join(document_data.keys())
                    placeholders = ', '.join(['?'] * len(document_data))
                    values = list(document_data.values())
                    
                    cursor.execute(f"INSERT INTO documents ({fields}) VALUES ({placeholders})", values)
                    document_id = cursor.lastrowid
                    
                    # Store mapping
                    ga4_id_to_db_id[document_data['ga4_id']] = document_id
                    
                    documents_imported += 1
                    
                    if documents_imported % 1000 == 0:
                        logger.info(f"Imported {documents_imported} documents so far")
                        conn.commit()
                
                except Exception as e:
                    logger.error(f"Error processing document row: {e}")
            
            conn.commit()
            logger.info(f"Imported {documents_imported} documents")
        
        # Import line items if file exists
        if os.path.exists(line_items_file):
            import_line_items(line_items_file, ga4_id_to_db_id, conn)
        
        # Import document extras if file exists
        if os.path.exists(document_extras_file):
            import_document_extras(document_extras_file, ga4_id_to_db_id, conn)
        
        conn.close()
        return True
    
    except Exception as e:
        logger.error(f"Error importing documents: {e}")
        conn.close()
        return False

def import_line_items(line_items_file, ga4_id_to_db_id, conn):
    """Import line items from GA4 exports"""
    logger.info(f"Importing line items from {line_items_file}")
    
    cursor = conn.cursor()
    
    try:
        with open(line_items_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            
            # Find relevant columns
            ga4_id_col = headers.index('_ID') if '_ID' in headers else -1
            doc_id_col = headers.index('_ID_Document') if '_ID_Document' in headers else -1
            
            # Look for line item columns
            desc_col = -1
            qty_col = -1
            price_col = -1
            total_col = -1
            tax_rate_col = -1
            tax_amount_col = -1
            item_type_col = -1
            part_number_col = -1
            labor_hours_col = -1
            
            for i, header in enumerate(headers):
                header_lower = header.lower()
                if 'description' in header_lower or 'desc' in header_lower:
                    desc_col = i
                elif 'quantity' in header_lower or 'qty' in header_lower:
                    qty_col = i
                elif 'price' in header_lower and 'unit' in header_lower:
                    price_col = i
                elif 'total' in header_lower and 'price' in header_lower:
                    total_col = i
                elif 'tax' in header_lower and 'rate' in header_lower:
                    tax_rate_col = i
                elif 'tax' in header_lower and 'amount' in header_lower:
                    tax_amount_col = i
                elif 'type' in header_lower:
                    item_type_col = i
                elif 'part' in header_lower and 'number' in header_lower:
                    part_number_col = i
                elif 'labor' in header_lower and 'hours' in header_lower:
                    labor_hours_col = i
            
            # Process line items
            line_items_imported = 0
            
            for row in reader:
                try:
                    # Skip empty rows
                    if not row or len(row) < 3:
                        continue
                    
                    # Extract line item data
                    line_item_data = {}
                    
                    # Get GA4 ID
                    if ga4_id_col >= 0 and ga4_id_col < len(row):
                        ga4_id = row[ga4_id_col].strip()
                        if ga4_id:
                            line_item_data['ga4_id'] = ga4_id
                    
                    # Get document ID
                    document_id = None
                    if doc_id_col >= 0 and doc_id_col < len(row):
                        doc_ga4_id = row[doc_id_col].strip()
                        if doc_ga4_id and doc_ga4_id in ga4_id_to_db_id:
                            document_id = ga4_id_to_db_id[doc_ga4_id]
                            line_item_data['document_id'] = document_id
                    
                    # Skip if no document ID
                    if 'document_id' not in line_item_data:
                        continue
                    
                    # Get description
                    if desc_col >= 0 and desc_col < len(row):
                        desc = row[desc_col].strip()
                        if desc:
                            line_item_data['description'] = desc
                    
                    # Get quantity
                    if qty_col >= 0 and qty_col < len(row):
                        qty = row[qty_col].strip()
                        if qty:
                            try:
                                line_item_data['quantity'] = float(qty.replace(',', ''))
                            except ValueError:
                                pass
                    
                    # Get unit price
                    if price_col >= 0 and price_col < len(row):
                        price = row[price_col].strip()
                        if price:
                            try:
                                line_item_data['unit_price'] = float(price.replace(',', ''))
                            except ValueError:
                                pass
                    
                    # Get total price
                    if total_col >= 0 and total_col < len(row):
                        total = row[total_col].strip()
                        if total:
                            try:
                                line_item_data['total_price'] = float(total.replace(',', ''))
                            except ValueError:
                                pass
                    
                    # Get tax rate
                    if tax_rate_col >= 0 and tax_rate_col < len(row):
                        tax_rate = row[tax_rate_col].strip()
                        if tax_rate:
                            try:
                                line_item_data['tax_rate'] = float(tax_rate.replace(',', '').replace('%', ''))
                            except ValueError:
                                pass
                    
                    # Get tax amount
                    if tax_amount_col >= 0 and tax_amount_col < len(row):
                        tax_amount = row[tax_amount_col].strip()
                        if tax_amount:
                            try:
                                line_item_data['tax_amount'] = float(tax_amount.replace(',', ''))
                            except ValueError:
                                pass
                    
                    # Get item type
                    if item_type_col >= 0 and item_type_col < len(row):
                        item_type = row[item_type_col].strip()
                        if item_type:
                            line_item_data['item_type'] = item_type
                    
                    # Get part number
                    if part_number_col >= 0 and part_number_col < len(row):
                        part_number = row[part_number_col].strip()
                        if part_number:
                            line_item_data['part_number'] = part_number
                    
                    # Get labor hours
                    if labor_hours_col >= 0 and labor_hours_col < len(row):
                        labor_hours = row[labor_hours_col].strip()
                        if labor_hours:
                            try:
                                line_item_data['labor_hours'] = float(labor_hours.replace(',', ''))
                            except ValueError:
                                pass
                    
                    # Insert line item
                    if len(line_item_data) > 1:  # More than just document_id
                        fields = ', '.join(line_item_data.keys())
                        placeholders = ', '.join(['?'] * len(line_item_data))
                        values = list(line_item_data.values())
                        
                        cursor.execute(f"INSERT INTO line_items ({fields}) VALUES ({placeholders})", values)
                        line_items_imported += 1
                        
                        if line_items_imported % 1000 == 0:
                            logger.info(f"Imported {line_items_imported} line items so far")
                            conn.commit()
                
                except Exception as e:
                    logger.error(f"Error processing line item row: {e}")
            
            conn.commit()
            logger.info(f"Imported {line_items_imported} line items")
    
    except Exception as e:
        logger.error(f"Error importing line items: {e}")

def import_document_extras(document_extras_file, ga4_id_to_db_id, conn):
    """Import document extras from GA4 exports"""
    logger.info(f"Importing document extras from {document_extras_file}")
    
    cursor = conn.cursor()
    
    try:
        with open(document_extras_file, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.reader(f)
            headers = next(reader, [])
            
            # Find relevant columns
            doc_id_col = headers.index('_ID_Document') if '_ID_Document' in headers else -1
            
            # Process document extras
            extras_imported = 0
            
            for row in reader:
                try:
                    # Skip empty rows
                    if not row or len(row) < 3:
                        continue
                    
                    # Get document ID
                    document_id = None
                    if doc_id_col >= 0 and doc_id_col < len(row):
                        doc_ga4_id = row[doc_id_col].strip()
                        if doc_ga4_id and doc_ga4_id in ga4_id_to_db_id:
                            document_id = ga4_id_to_db_id[doc_ga4_id]
                    
                    # Skip if no document ID
                    if not document_id:
                        continue
                    
                    # Process each field in the row
                    for i, header in enumerate(headers):
                        if i != doc_id_col and i < len(row) and row[i].strip():
                            field_name = header.strip()
                            field_value = row[i].strip()
                            
                            # Insert document extra
                            cursor.execute("""
                            INSERT INTO document_extras (document_id, field_name, field_value)
                            VALUES (?, ?, ?)
                            """, (document_id, field_name, field_value))
                            
                            extras_imported += 1
                    
                    if extras_imported % 1000 == 0:
                        logger.info(f"Imported {extras_imported} document extras so far")
                        conn.commit()
                
                except Exception as e:
                    logger.error(f"Error processing document extra row: {e}")
            
            conn.commit()
            logger.info(f"Imported {extras_imported} document extras")
    
    except Exception as e:
        logger.error(f"Error importing document extras: {e}")

def get_document_by_id(document_id):
    """Get document by ID with related data"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get document
    cursor.execute("""
    SELECT d.*, c.name as customer_name, v.registration as vehicle_registration,
           v.make as vehicle_make, v.model as vehicle_model
    FROM documents d
    LEFT JOIN customers c ON d.customer_id = c.id
    LEFT JOIN vehicles v ON d.vehicle_id = v.id
    WHERE d.id = ?
    """, (document_id,))
    
    document = cursor.fetchone()
    
    if not document:
        conn.close()
        return None
    
    # Get line items
    cursor.execute("""
    SELECT * FROM line_items
    WHERE document_id = ?
    ORDER BY id
    """, (document_id,))
    
    line_items = cursor.fetchall()
    
    # Get document extras
    cursor.execute("""
    SELECT * FROM document_extras
    WHERE document_id = ?
    ORDER BY field_name
    """, (document_id,))
    
    extras = cursor.fetchall()
    
    conn.close()
    
    # Convert to dict
    document_dict = dict(document)
    document_dict['line_items'] = [dict(item) for item in line_items]
    document_dict['extras'] = [dict(extra) for extra in extras]
    
    return document_dict

def get_documents(filters=None, page=1, per_page=20):
    """Get documents with optional filtering and pagination"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Build query
    query = """
    SELECT d.id, d.document_number, d.document_type, d.document_date,
           d.total_amount, d.status, c.name as customer_name,
           v.registration as vehicle_registration
    FROM documents d
    LEFT JOIN customers c ON d.customer_id = c.id
    LEFT JOIN vehicles v ON d.vehicle_id = v.id
    """
    
    params = []
    
    # Add filters
    if filters:
        where_clauses = []
        
        if 'document_type' in filters and filters['document_type']:
            where_clauses.append("d.document_type = ?")
            params.append(filters['document_type'])
        
        if 'customer_id' in filters and filters['customer_id']:
            where_clauses.append("d.customer_id = ?")
            params.append(filters['customer_id'])
        
        if 'vehicle_id' in filters and filters['vehicle_id']:
            where_clauses.append("d.vehicle_id = ?")
            params.append(filters['vehicle_id'])
        
        if 'date_from' in filters and filters['date_from']:
            where_clauses.append("d.document_date >= ?")
            params.append(filters['date_from'])
        
        if 'date_to' in filters and filters['date_to']:
            where_clauses.append("d.document_date <= ?")
            params.append(filters['date_to'])
        
        if 'search' in filters and filters['search']:
            search_term = f"%{filters['search']}%"
            where_clauses.append("""(
                d.document_number LIKE ? OR
                d.document_type LIKE ? OR
                c.name LIKE ? OR
                v.registration LIKE ?
            )""")
            params.extend([search_term, search_term, search_term, search_term])
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
    
    # Add ordering
    query += " ORDER BY d.document_date DESC"
    
    # Count total
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    
    # Add pagination
    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    
    # Execute query
    cursor.execute(query, params)
    documents = cursor.fetchall()
    
    conn.close()
    
    # Convert to dict
    documents_list = [dict(doc) for doc in documents]
    
    return {
        'documents': documents_list,
        'total': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': (total_count + per_page - 1) // per_page
    }

def get_document_types():
    """Get list of document types"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT DISTINCT document_type
    FROM documents
    WHERE document_type IS NOT NULL
    ORDER BY document_type
    """)
    
    types = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return types

def get_customer_documents(customer_id):
    """Get documents for a specific customer"""
    return get_documents({'customer_id': customer_id})

def get_vehicle_documents(vehicle_id):
    """Get documents for a specific vehicle"""
    return get_documents({'vehicle_id': vehicle_id})

if __name__ == "__main__":
    logger.info("Starting GA4 Document Browser")
    import_documents()
    logger.info("GA4 Document Browser completed")
