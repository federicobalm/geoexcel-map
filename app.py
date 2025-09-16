import os
import json
import webbrowser
import shutil
from threading import Timer
import secrets
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, send_from_directory, flash, send_file
from werkzeug.utils import secure_filename
from datetime import datetime
import socket
import pandas as pd

from tools.db_models import db, Project
from tools.excel_processor import process_data, read_data_file
from tools.map_generator import create_map
from tools.export_handler import export_to_html, export_to_pdf, export_to_kmz

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(DATA_DIR, "projects.db")}'
app.config['UPLOAD_FOLDER'] = os.path.join(DATA_DIR, 'uploads')
app.config['PROJECTS_DATA_FOLDER'] = os.path.join(DATA_DIR, 'projects')
app.config['SESSION_MAPS_FOLDER'] = os.path.join(DATA_DIR, 'session_maps')

db.init_app(app)
with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROJECTS_DATA_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SESSION_MAPS_FOLDER'], exist_ok=True)
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_map_step1():
    if 'excel_file' not in request.files: flash('No se seleccionó ningún archivo', 'danger'); return redirect(url_for('index'))
    file = request.files['excel_file']
    if file.filename == '': flash('Archivo no válido.', 'danger'); return redirect(url_for('index'))
    
    filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    session.clear(); session['form_data'] = request.form.to_dict(); session['excel_path'] = filepath
    
    analysis_result = process_data(filepath)
    if 'error' in analysis_result:
        flash(analysis_result['error'], 'danger'); return redirect(url_for('index'))

    if analysis_result.get('success'):
        session['lat_lon_cols'] = analysis_result['columns']
        return redirect(url_for('generate_map_final'))
    else:
        df = read_data_file(filepath)
        if isinstance(df, dict) and 'error' in df:
            flash(df['error'], 'danger'); return redirect(url_for('index'))
        
        df_preview = df.head().to_html(classes='table table-sm table-striped table-bordered', index=False, border=0)
        return render_template('select_columns.html', 
                               options=analysis_result['all_columns'], 
                               df_preview=df_preview)

@app.route('/generate_step2', methods=['POST'])
def generate_map_step2():
    if 'excel_path' not in session: return redirect(url_for('index'))
    session['lat_lon_cols'] = {'lat': request.form['lat_col'], 'lon': request.form['lon_col']}
    return redirect(url_for('generate_map_final'))

@app.route('/generate_final', methods=['GET'])
def generate_map_final():
    if 'excel_path' not in session: return redirect(url_for('index'))
    
    df = process_data(session['excel_path'], session['lat_lon_cols'])
    if df.empty: flash('No se encontraron coordenadas válidas.', 'warning'); return redirect(url_for('index'))
    
    map_params = session['form_data']
    folium_map = create_map(df, map_params, session['lat_lon_cols'])
    
    unique_token = secrets.token_hex(8)
    temp_map_filename = f"session_{unique_token}.html"
    temp_map_path = os.path.join(app.config['SESSION_MAPS_FOLDER'], temp_map_filename)
    folium_map.save(temp_map_path); session['temp_map_path'] = temp_map_path
    map_url = url_for('serve_session_map', filename=temp_map_filename)
    
    return render_template('index.html', map_url=map_url, form_data=map_params)

@app.route('/save_project', methods=['POST'])
def save_project():
    if 'excel_path' not in session:
        flash('No hay datos para guardar.', 'warning')
        return redirect(url_for('index'))
    project_name = request.form.get('project_name', 'Proyecto sin nombre')
    map_params = session['form_data']
    new_project = Project(
        name=project_name, map_type=map_params.get('map_type'),
        map_params=json.dumps(map_params), lat_lon_cols=json.dumps(session['lat_lon_cols'])
    )
    db.session.add(new_project)
    db.session.commit()
    project_dir = os.path.join(app.config['PROJECTS_DATA_FOLDER'], str(new_project.id))
    maps_dir = os.path.join(project_dir, 'maps')
    os.makedirs(maps_dir, exist_ok=True)
    new_excel_path = os.path.join(project_dir, 'source.xlsx')
    shutil.move(session['excel_path'], new_excel_path)
    new_project.excel_path = new_excel_path
    if 'temp_map_path' in session and os.path.exists(session['temp_map_path']):
        map_filepath = os.path.join(maps_dir, f'map_{datetime.now().strftime("%Y%m%d%H%M%S")}.html')
        shutil.move(session['temp_map_path'], map_filepath)
        new_project.latest_map_html = map_filepath
    db.session.commit()
    session.clear()
    flash(f'Proyecto "{project_name}" guardado.', 'success')
    return redirect(url_for('view_project', id=new_project.id))

@app.route('/projects')
def list_projects():
    projects = Project.query.filter_by(is_deleted=False).order_by(Project.created_at.desc()).all()
    return render_template('projects.html', projects=projects)

@app.route('/projects/<int:id>')
def view_project(id):
    project = db.get_or_404(Project, id)
    return render_template('project_view.html', project=project)

@app.route('/session_map/<filename>')
def serve_session_map(filename):
    return send_from_directory(app.config['SESSION_MAPS_FOLDER'], filename)

@app.route('/project_map/<int:id>')
def serve_project_map(id):
    project = db.get_or_404(Project, id)
    return send_file(project.latest_map_html)

@app.route('/projects/<int:id>/export_html')
def get_export_html(id):
    return export_to_html(db.get_or_404(Project, id))

@app.route('/projects/<int:id>/export_pdf')
def get_export_pdf(id):
    return export_to_pdf(db.get_or_404(Project, id), get_user_info_dict())

@app.route('/projects/<int:id>/export_kmz')
def get_export_kmz(id):
    return export_to_kmz(db.get_or_404(Project, id))

@app.route('/projects/<int:id>/delete', methods=['POST'])
def delete_project(id):
    project = db.get_or_404(Project, id)
    project.is_deleted = True
    db.session.commit()
    flash(f'Proyecto "{project.name}" eliminado.', 'info')
    return redirect(url_for('list_projects'))

@app.route('/sample')
def download_sample():
    return send_from_directory('sample_data', 'ejemplo.xlsx', as_attachment=True)

def get_user_info_dict():
    if not os.path.exists(USER_DATA_FILE): return {}
    with open(USER_DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)

@app.route('/about_user')
def get_user_info_json():
    user_data = get_user_info_dict()
    if not user_data: return jsonify({'error': 'Archivo no encontrado'}), 404
    return jsonify(user_data)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1)); IP = s.getsockname()[0]
    except Exception: IP = '127.0.0.1'
    finally: s.close()
    return IP

def open_browser():
      webbrowser.open_new(f"http://{get_local_ip()}:5000")

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f" * Accede a la aplicación desde cualquier dispositivo en tu red en: http://{local_ip}:5000")
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        if 'DISPLAY' in os.environ or os.name == 'nt':
             Timer(1, open_browser).start()
    app.run(host='0.0.0.0', port=5000, debug=False)