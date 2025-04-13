#!/usr/bin/env python3
"""
Document Routes Module

This module handles routes related to document management.
"""

import os
import logging
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import render_template, redirect, url_for, flash, request, send_file

from app import app
from app.utils.database import get_db_connection

logger = logging.getLogger(__name__)

# Get database path from app config
db_path = app.config.get('DATABASE_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'garage_system.db'))

# Set up document storage directory
DOCUMENT_UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'documents')
if not os.path.exists(DOCUMENT_UPLOAD_FOLDER):
    os.makedirs(DOCUMENT_UPLOAD_FOLDER)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx', 'txt'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/documents')
def documents():
    """Documents page"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get documents with customer and vehicle info
        cursor.execute("""
        SELECT d.id, d.document_type, d.filename, d.file_path, d.created_at,
               c.id as customer_id, c.name as customer_name,
               v.id as vehicle_id, v.registration
        FROM documents d
        LEFT JOIN customers c ON d.customer_id = c.id
        LEFT JOIN vehicles v ON d.vehicle_id = v.id
        ORDER BY d.created_at DESC
        """)
        
        documents_data = cursor.fetchall()
        
        # Get total counts for statistics
        cursor.execute("""
        SELECT 
            COUNT(*) as total_documents,
            COUNT(DISTINCT customer_id) as customer_documents,
            COUNT(DISTINCT vehicle_id) as vehicle_documents
        FROM documents
        """)
        
        stats = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        return render_template('documents.html', 
                               documents=documents_data, 
                               stats=stats,
                               now=datetime.now())
    
    except Exception as e:
        logger.error(f"Error displaying documents: {e}")
        flash(f'Error displaying documents: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/documents/upload', methods=['GET', 'POST'])
def upload_document():
    """Upload a new document"""
    if request.method == 'POST':
        try:
            # Get form data
            customer_id = request.form.get('customer_id')
            vehicle_id = request.form.get('vehicle_id')
            document_type = request.form.get('document_type')
            
            # Check if the post request has the file part
            if 'document' not in request.files:
                flash('No file part', 'danger')
                return redirect(request.url)
            
            file = request.files['document']
            
            # If user does not select file, browser also
            # submit an empty part without filename
            if file.filename == '':
                flash('No selected file', 'danger')
                return redirect(request.url)
            
            # Check if file type is allowed
            if not allowed_file(file.filename):
                flash(f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}', 'danger')
                return redirect(request.url)
            
            # Validate data
            if not document_type:
                flash('Please select a document type', 'danger')
                return redirect(request.url)
            
            if not customer_id and not vehicle_id:
                flash('Please select a customer or vehicle', 'danger')
                return redirect(request.url)
            
            # Secure filename
            filename = secure_filename(file.filename)
            
            # Create unique filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # Create customer/vehicle subdirectory if needed
            if customer_id:
                upload_dir = os.path.join(DOCUMENT_UPLOAD_FOLDER, f"customer_{customer_id}")
            else:
                upload_dir = os.path.join(DOCUMENT_UPLOAD_FOLDER, f"vehicle_{vehicle_id}")
            
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            
            # Save file
            file_path = os.path.join(upload_dir, unique_filename)
            file.save(file_path)
            
            # Connect to database
            conn = get_db_connection(db_path)
            cursor = conn.cursor()
            
            # Add document to database
            cursor.execute("""
            INSERT INTO documents (
                customer_id, vehicle_id, document_type, filename, file_path, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id if customer_id else None,
                vehicle_id if vehicle_id else None,
                document_type,
                filename,
                file_path,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            # Commit changes
            conn.commit()
            conn.close()
            
            flash('Document uploaded successfully', 'success')
            return redirect(url_for('documents'))
        
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            flash(f'Error uploading document: {e}', 'danger')
            return redirect(url_for('upload_document'))
    
    # GET request
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get customers
        cursor.execute("""
        SELECT id, name
        FROM customers
        ORDER BY name
        """)
        
        customers = cursor.fetchall()
        
        # Get vehicles
        cursor.execute("""
        SELECT v.id, v.registration, v.make, v.model,
               c.id as customer_id, c.name as customer_name
        FROM vehicles v
        LEFT JOIN customers c ON v.customer_id = c.id
        ORDER BY v.registration
        """)
        
        vehicles = cursor.fetchall()
        
        # Close connection
        conn.close()
        
        return render_template('upload_document.html', 
                               customers=customers,
                               vehicles=vehicles,
                               document_types=['MOT Certificate', 'Service Record', 'Invoice', 'Insurance', 'Tax', 'Other'])
    
    except Exception as e:
        logger.error(f"Error loading upload document form: {e}")
        flash(f'Error loading upload document form: {e}', 'danger')
        return redirect(url_for('documents'))

@app.route('/documents/download/<int:document_id>')
def download_document(document_id):
    """Download a document"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get document
        cursor.execute("""
        SELECT id, filename, file_path
        FROM documents
        WHERE id = ?
        """, (document_id,))
        
        document = cursor.fetchone()
        
        # Close connection
        conn.close()
        
        if not document:
            flash('Document not found', 'danger')
            return redirect(url_for('documents'))
        
        # Check if file exists
        if not os.path.exists(document['file_path']):
            flash('Document file not found', 'danger')
            return redirect(url_for('documents'))
        
        # Send file
        return send_file(document['file_path'], as_attachment=True, download_name=document['filename'])
    
    except Exception as e:
        logger.error(f"Error downloading document: {e}")
        flash(f'Error downloading document: {e}', 'danger')
        return redirect(url_for('documents'))

@app.route('/documents/delete/<int:document_id>')
def delete_document(document_id):
    """Delete a document"""
    try:
        # Connect to database
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Get document
        cursor.execute("""
        SELECT id, file_path
        FROM documents
        WHERE id = ?
        """, (document_id,))
        
        document = cursor.fetchone()
        
        if not document:
            flash('Document not found', 'danger')
            conn.close()
            return redirect(url_for('documents'))
        
        # Delete file if it exists
        if os.path.exists(document['file_path']):
            os.remove(document['file_path'])
        
        # Delete document from database
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        
        # Commit changes
        conn.commit()
        conn.close()
        
        flash('Document deleted successfully', 'success')
        return redirect(url_for('documents'))
    
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        flash(f'Error deleting document: {e}', 'danger')
        return redirect(url_for('documents'))
