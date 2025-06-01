import streamlit as st
import os
import time
import pandas as pd
import psutil
from pathlib import Path
import platform
import subprocess
import webbrowser

from file_scanner import FileScanner
from file_organizer import FileOrganizer
from file_monitor import FileMonitor
import utils

# Custom CSS for beautiful styling and theme toggle
def load_css():
    dark_theme = st.session_state.get('dark_theme', False)
    
    if dark_theme:
        css = """
        <style>
        .stApp {
            background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
            color: #ffffff;
        }
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .feature-card {
            background: rgba(255,255,255,0.1);
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .action-button {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .file-action-card {
            background: rgba(255,255,255,0.1);
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            border-left: 4px solid #667eea;
        }
        </style>
        """
    else:
        css = """
        <style>
        .stApp {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            color: white;
            margin-bottom: 2rem;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        .feature-card {
            background: rgba(255,255,255,0.9);
            padding: 1.5rem;
            border-radius: 10px;
            margin: 1rem 0;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        }
        .action-button {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        .file-action-card {
            background: rgba(255,255,255,0.95);
            padding: 1rem;
            border-radius: 8px;
            margin: 0.5rem 0;
            border-left: 4px solid #667eea;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .splash-screen {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            color: white;
            font-size: 3rem;
            font-weight: bold;
        }
        </style>
        """
    
    st.markdown(css, unsafe_allow_html=True)

# Splash screen function
def show_splash_screen():
    if 'splash_shown' not in st.session_state:
        st.session_state.splash_shown = False
    
    if not st.session_state.splash_shown:
        splash_placeholder = st.empty()
        with splash_placeholder.container():
            st.markdown("""
            <div class="splash-screen">
                <div style="text-align: center;">
                    <h1>🤖 DupliFinder AI</h1>
                    <p style="font-size: 1.5rem; margin-top: 1rem;">Intelligent File Duplicate Detection</p>
                    <div style="margin-top: 2rem;">
                        <div style="width: 50px; height: 50px; border: 5px solid #f3f3f3; border-top: 5px solid #ffffff; border-radius: 50%; animation: spin 2s linear infinite; margin: 0 auto;"></div>
                    </div>
                </div>
            </div>
            <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            </style>
            """, unsafe_allow_html=True)
        
        time.sleep(2)
        st.session_state.splash_shown = True
        splash_placeholder.empty()
        st.rerun()

# Get all available drives
def get_all_drives():
    drives = []
    if platform.system() == "Windows":
        for partition in psutil.disk_partitions():
            drives.append(partition.mountpoint)
    else:
        drives = ["/"]
    return drives

# File operations
def open_file(file_path):
    """Open file with default application"""
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", file_path])
        else:  # Linux
            subprocess.call(["xdg-open", file_path])
        return True
    except Exception as e:
        st.error(f"❌ Failed to open file: {str(e)}")
        return False

def open_file_location(file_path):
    """Open file location in file explorer"""
    try:
        directory = os.path.dirname(file_path)
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer /select,"{file_path}"')
        elif platform.system() == "Darwin":  # macOS
            subprocess.call(["open", "-R", file_path])
        else:  # Linux
            subprocess.call(["xdg-open", directory])
        return True
    except Exception as e:
        st.error(f"❌ Failed to open file location: {str(e)}")
        return False

# Helper functions for file deletion with confirmation
def _delete_older_duplicates(files, group_index):
    """Delete all but the newest file in a duplicate group with confirmation"""
    sorted_files = sorted(files, key=lambda f: f.modified, reverse=True)
    
    st.markdown("""
    <div class="feature-card">
        <h4 style="color: #667eea;">📋 Deletion Plan</h4>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("**Will KEEP (newest):**")
    st.success(f"✅ {os.path.basename(sorted_files[0].path)} - {sorted_files[0].path}")
    
    st.write("**Will DELETE:**")
    files_to_delete = sorted_files[1:]
    for file_info in files_to_delete:
        st.error(f"❌ {os.path.basename(file_info.path)} - {file_info.path}")
    
    if st.button(f"🗑️ CONFIRM Delete {len(files_to_delete)} older files", key=f"confirm_keep_newest_{group_index}"):
        deleted_count = 0
        deleted_files = []
        for file_info in files_to_delete:
            try:
                os.remove(file_info.path)
                deleted_count += 1
                deleted_files.append(os.path.basename(file_info.path))
            except Exception as e:
                st.error(f"Failed to delete {os.path.basename(file_info.path)}: {str(e)}")
        
        if deleted_count > 0:
            st.success(f"✅ Successfully deleted {deleted_count} files: {', '.join(deleted_files)}")
            _update_scan_results_after_deletion()
        else:
            st.warning("No files were deleted")

def _delete_all_duplicates(files, group_index):
    """Delete all files in a duplicate group with confirmation"""
    st.markdown("""
    <div class="feature-card">
        <h4 style="color: #e74c3c;">⚠️ Delete All Files</h4>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("**Will DELETE ALL files in this group:**")
    file_names = []
    for file_info in files:
        file_name = os.path.basename(file_info.path)
        file_names.append(file_name)
        st.error(f"❌ {file_name} - {file_info.path}")
    
    st.warning("⚠️ This will delete ALL files in this group!")
    
    if st.button(f"🗑️ CONFIRM Delete ALL {len(files)} files: {', '.join(file_names[:3])}{'...' if len(file_names) > 3 else ''}", key=f"confirm_delete_all_{group_index}"):
        deleted_count = 0
        deleted_files = []
        for file_info in files:
            try:
                os.remove(file_info.path)
                deleted_count += 1
                deleted_files.append(os.path.basename(file_info.path))
            except Exception as e:
                st.error(f"Failed to delete {os.path.basename(file_info.path)}: {str(e)}")
        
        if deleted_count > 0:
            st.success(f"✅ Successfully deleted all {deleted_count} files: {', '.join(deleted_files)}")
            _update_scan_results_after_deletion()
        else:
            st.warning("No files were deleted")

def _delete_selected_files(files_to_delete, group_index):
    """Delete specific selected files with confirmation"""
    if len(files_to_delete) == 0:
        st.warning("No files selected for deletion")
        return
    
    st.markdown("""
    <div class="feature-card">
        <h4 style="color: #f39c12;">📂 Selected Files for Deletion</h4>
    </div>
    """, unsafe_allow_html=True)
    
    selected_names = []
    for file_info in files_to_delete:
        file_name = os.path.basename(file_info.path)
        selected_names.append(file_name)
        st.error(f"❌ {file_name} - {file_info.path}")
    
    if st.button(f"🗑️ CONFIRM Delete {len(files_to_delete)} files: {', '.join(selected_names[:3])}{'...' if len(selected_names) > 3 else ''}", key=f"confirm_selected_{group_index}"):
        deleted_count = 0
        deleted_files = []
        for file_info in files_to_delete:
            try:
                os.remove(file_info.path)
                deleted_count += 1
                deleted_files.append(os.path.basename(file_info.path))
            except Exception as e:
                st.error(f"Failed to delete {os.path.basename(file_info.path)}: {str(e)}")
        
        if deleted_count > 0:
            st.success(f"✅ Successfully deleted {deleted_count} files: {', '.join(deleted_files)}")
            _update_scan_results_after_deletion()
        else:
            st.warning("No files were selected for deletion")

def _update_scan_results_after_deletion():
    """Update scan results after files have been deleted"""
    if st.session_state.scanner:
        st.session_state.scanner.inventory_files()
        list(st.session_state.scanner.process_files())
        st.session_state.scan_results = st.session_state.scanner.get_duplicate_groups()
        st.rerun()

def display_scan_results():
    """Display scan results with file actions"""
    if st.session_state.scan_results:
        # Separate content matches and filename matches
        content_matches = {}
        filename_matches = {}
        
        for hash_val, files in st.session_state.scan_results.items():
            if len(files) > 1:
                first_file = files[0]
                has_same_content = all(f.content_hash == first_file.content_hash for f in files if f.content_hash)
                
                if has_same_content:
                    content_matches[hash_val] = files
                else:
                    for file in files:
                        if file.name not in filename_matches:
                            filename_matches[file.name] = []
                        filename_matches[file.name].append(file)
        
        # Display statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔄 Content Match Groups", len(content_matches))
        with col2:
            st.metric("📝 Filename Match Groups", len(filename_matches))
        with col3:
            total_duplicates = sum(len(files) for files in content_matches.values())
            st.metric("📄 Total Duplicate Files", total_duplicates)
        
        # Content matches section
        if content_matches:
            st.markdown("""
            <div class="feature-card">
                <h4>🔄 Files with Identical Content</h4>
            </div>
            """, unsafe_allow_html=True)
            
            for i, (hash_value, files) in enumerate(content_matches.items()):
                with st.expander(f"📁 Group {i+1} ({len(files)} matching files)", expanded=True):
                    # File details with action buttons
                    for j, file_info in enumerate(files):
                        st.markdown(f"""
                        <div class="file-action-card">
                            <h5>📄 {os.path.basename(file_info.path)}</h5>
                            <p><strong>📂 Path:</strong> {file_info.path}</p>
                            <p><strong>💾 Size:</strong> {file_info.size / 1024:.2f} KB | <strong>📅 Modified:</strong> {file_info.modified.strftime("%Y-%m-%d %H:%M")}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # File action buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button(f"📂 Open File", key=f"open_file_{i}_{j}"):
                                if open_file(file_info.path):
                                    st.success(f"✅ Opened: {os.path.basename(file_info.path)}")
                        
                        with col2:
                            if st.button(f"📍 Open Location", key=f"open_location_{i}_{j}"):
                                if open_file_location(file_info.path):
                                    st.success(f"✅ Opened location for: {os.path.basename(file_info.path)}")
                        
                        with col3:
                            if st.button(f"🗑️ Delete {os.path.basename(file_info.path)}", key=f"delete_single_{i}_{j}"):
                                try:
                                    os.remove(file_info.path)
                                    st.success(f"✅ Deleted: {os.path.basename(file_info.path)}")
                                    _update_scan_results_after_deletion()
                                except Exception as e:
                                    st.error(f"❌ Failed to delete {os.path.basename(file_info.path)}: {str(e)}")
                        
                        st.divider()
                    
                    # Group action buttons
                    st.markdown("### 🛠️ Group Actions")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(f"📅 Keep Newest Only", key=f"keep_newest_{i}", type="secondary"):
                            st.session_state[f"show_keep_newest_{i}"] = True
                    
                    with col2:
                        if st.button(f"🗑️ Delete All Files", key=f"delete_all_{i}", type="secondary"):
                            st.session_state[f"show_delete_all_{i}"] = True
                    
                    with col3:
                        if st.button(f"✅ Select Files to Delete", key=f"select_delete_{i}", type="secondary"):
                            st.session_state[f"show_selection_{i}"] = True
                    
                    # Show confirmation dialogs
                    if st.session_state.get(f"show_keep_newest_{i}", False):
                        st.divider()
                        _delete_older_duplicates(files, i)
                        if st.button(f"❌ Cancel", key=f"cancel_keep_newest_{i}"):
                            st.session_state[f"show_keep_newest_{i}"] = False
                            st.rerun()
                    
                    if st.session_state.get(f"show_delete_all_{i}", False):
                        st.divider()
                        _delete_all_duplicates(files, i)
                        if st.button(f"❌ Cancel", key=f"cancel_delete_all_{i}"):
                            st.session_state[f"show_delete_all_{i}"] = False
                            st.rerun()
                    
                    if st.session_state.get(f"show_selection_{i}", False):
                        st.divider()
                        st.write("**Select files to delete:**")
                        files_to_delete = []
                        for j, file_info in enumerate(files):
                            if st.checkbox(f"🗑️ Delete: {os.path.basename(file_info.path)}", key=f"select_{i}_{j}"):
                                files_to_delete.append(file_info)
                        
                        if len(files_to_delete) > 0:
                            _delete_selected_files(files_to_delete, i)
                        
                        if st.button(f"❌ Cancel Selection", key=f"cancel_selection_{i}"):
                            st.session_state[f"show_selection_{i}"] = False
                            st.rerun()
        
        # Filename matches section
        if filename_matches:
            st.markdown("""
            <div class="feature-card">
                <h4>📝 Files with Same Names (Different Content)</h4>
            </div>
            """, unsafe_allow_html=True)
            
            for k, (filename, files) in enumerate(filename_matches.items()):
                if len(files) > 1:
                    with st.expander(f"📝 Name Group {k+1} ({len(files)} files with same name)", expanded=True):
                        for j, file_info in enumerate(files):
                            st.markdown(f"""
                            <div class="file-action-card">
                                <h5>📄 {os.path.basename(file_info.path)}</h5>
                                <p><strong>📂 Path:</strong> {file_info.path}</p>
                                <p><strong>💾 Size:</strong> {file_info.size / 1024:.2f} KB | <strong>📅 Modified:</strong> {file_info.modified.strftime("%Y-%m-%d %H:%M")}</p>
                                <p><strong>🔍 Content Hash:</strong> {file_info.content_hash[:8] if file_info.content_hash else "N/A"}...</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # File action buttons
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if st.button(f"📂 Open File", key=f"open_name_file_{filename}_{j}"):
                                    if open_file(file_info.path):
                                        st.success(f"✅ Opened: {os.path.basename(file_info.path)}")
                            
                            with col2:
                                if st.button(f"📍 Open Location", key=f"open_name_location_{filename}_{j}"):
                                    if open_file_location(file_info.path):
                                        st.success(f"✅ Opened location for: {os.path.basename(file_info.path)}")
                            
                            with col3:
                                if st.button(f"🗑️ Delete {os.path.basename(file_info.path)}", key=f"delete_name_single_{filename}_{j}"):
                                    try:
                                        os.remove(file_info.path)
                                        st.success(f"✅ Deleted: {os.path.basename(file_info.path)}")
                                        _update_scan_results_after_deletion()
                                    except Exception as e:
                                        st.error(f"❌ Failed to delete {os.path.basename(file_info.path)}: {str(e)}")
                            
                            st.divider()
    else:
        st.success("✅ No duplicate files found!")

# Set page config
st.set_page_config(
    page_title="DupliFinder AI - Intelligent File Management",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS and show splash screen
load_css()
show_splash_screen()

# Theme toggle button
col1, col2 = st.columns([10, 1])
with col2:
    if st.button("🌙/☀️", key="theme_toggle", help="Toggle Dark/Light Mode"):
        st.session_state.dark_theme = not st.session_state.get('dark_theme', False)
        st.rerun()

# Initialize session state variables
if 'scanner' not in st.session_state:
    st.session_state.scanner = None
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = None
if 'scan_complete' not in st.session_state:
    st.session_state.scan_complete = False
if 'monitor_active' not in st.session_state:
    st.session_state.monitor_active = False
if 'monitor' not in st.session_state:
    st.session_state.monitor = None
if 'auto_scan_complete' not in st.session_state:
    st.session_state.auto_scan_complete = False

# Initialize selection states for file deletion
for i in range(100):
    for state in ['show_selection', 'show_keep_newest', 'show_delete_all']:
        if f'{state}_{i}' not in st.session_state:
            st.session_state[f'{state}_{i}'] = False

# Main header
st.markdown("""
<div class="main-header">
    <h1>🤖 DupliFinder AI</h1>
    <p>Intelligent File Duplicate Detection & Organization System</p>
    <p>🚀 Advanced AI-Powered File Management • 📁 Smart Organization • ⚡ Real-time Monitoring</p>
</div>
""", unsafe_allow_html=True)

# Auto-scan feature with advanced drive selection
st.markdown("""
<div class="feature-card">
    <h3>🔍 Smart Drive Scanner</h3>
    <p>Scan selected drives or all available drives for duplicate files (excludes Recycle Bin & system folders)</p>
</div>
""", unsafe_allow_html=True)

# Drive selection options
drives = get_all_drives()
col1, col2 = st.columns([2, 1])

with col1:
    with st.expander("⚙️ Advanced Drive Selection Options", expanded=True):
        scan_option = st.radio(
            "📁 Select Scan Mode:",
            options=["Scan All Available Drives", "Select Specific Drives", "Custom Directory"],
            index=0
        )
        
        selected_drives = []
        if scan_option == "Select Specific Drives":
            st.write("**Select drives to scan:**")
            for drive in drives:
                if st.checkbox(f"💾 {drive}", key=f"drive_{drive}", value=True):
                    selected_drives.append(drive)
        elif scan_option == "Custom Directory":
            custom_dir = st.text_input("📂 Enter custom directory path:", 
                                     value=str(Path.home()),
                                     help="Enter the full path to scan")
            if custom_dir and os.path.exists(custom_dir):
                selected_drives = [custom_dir]
        else:  # Scan All Available Drives
            selected_drives = drives
        
        # Scan options
        col_a, col_b = st.columns(2)
        with col_a:
            include_subdirs_auto = st.checkbox("📁 Include Subdirectories", value=True, key="auto_subdirs")
        with col_b:
            similarity_threshold_auto = st.slider("📄 PDF Similarity (%)", 50, 100, 100, key="auto_similarity")

    if st.button("🚀 Start Smart Scan", key="auto_scan_all", type="primary"):
        if selected_drives:
            st.session_state.auto_scan_complete = False
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            all_results = {}
            total_drives = len(selected_drives)
            
            for i, drive in enumerate(selected_drives):
                if os.path.exists(drive):
                    status_text.text(f"🔍 Scanning {drive}... (excludes Recycle Bin)")
                    
                    scanner = FileScanner(
                        base_directory=drive,
                        include_subdirs=include_subdirs_auto,
                        similarity_threshold=similarity_threshold_auto/100
                    )
                    
                    scanner.inventory_files()
                    list(scanner.process_files())
                    drive_results = scanner.get_duplicate_groups()
                    
                    # Merge results
                    for hash_val, files in drive_results.items():
                        if hash_val in all_results:
                            all_results[hash_val].extend(files)
                        else:
                            all_results[hash_val] = files
                    
                    progress_bar.progress((i + 1) / total_drives)
            
            st.session_state.scan_results = all_results
            st.session_state.auto_scan_complete = True
            st.session_state.scanner = scanner  # Store the last scanner
            progress_bar.progress(1.0)
            status_text.text("✅ Smart scan complete! Found duplicate groups below.")
            st.rerun()
        else:
            st.error("❌ Please select at least one drive or enter a valid directory!")

with col2:
    st.write("**Available Drives:**")
    for drive in drives:
        try:
            usage = psutil.disk_usage(drive)
            free_space = usage.free / (1024**3)  # Convert to GB
            total_space = usage.total / (1024**3)
            used_percent = (usage.used / usage.total) * 100
            st.write(f"💾 **{drive}**")
            st.write(f"   📊 {used_percent:.1f}% used")
            st.write(f"   💿 {free_space:.1f}GB free / {total_space:.1f}GB total")
        except:
            st.write(f"💾 {drive}")
    
    if scan_option == "Select Specific Drives" and selected_drives:
        st.write("**Selected for scan:**")
        for drive in selected_drives:
            st.success(f"✅ {drive}")

# Create tabs for different functions
tab_scanner, tab_organizer, tab_monitor = st.tabs([
    "🔍 File Scanner", 
    "📁 Organizer", 
    "👁️ Monitor"
])

with tab_scanner:
    st.markdown("""
    <div class="feature-card">
        <h3>🔍 Advanced File Scanner</h3>
        <p>Scan specific directories for duplicate files (excludes Recycle Bin & system folders)</p>
    </div>
    """, unsafe_allow_html=True)
    
    scan_directory = st.text_input("📂 Directory to Scan", 
                                  value=str(Path.home() / "Downloads"),
                                  help="Enter the full path to scan")
    
    with st.expander("⚙️ Advanced Options"):
        include_subdirs = st.checkbox("📁 Include Subdirectories", value=True)
        similarity_threshold = st.slider("📄 PDF Similarity Threshold (%)", 
                                        min_value=50, max_value=100, value=100)
        file_extensions = st.multiselect(
            "📎 File Extensions (leave empty for all)",
            options=[".pdf", ".docx", ".txt", ".jpg", ".png", ".mp3", ".mp4", ".zip"],
            default=[]
        )
    
    if st.button("🚀 Start Scan", key="start_scan", type="primary"):
        if os.path.exists(scan_directory):
            st.session_state.scanner = FileScanner(
                base_directory=scan_directory,
                include_subdirs=include_subdirs,
                similarity_threshold=similarity_threshold/100,
                file_extensions=file_extensions if file_extensions else None
            )
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("📋 Inventorying files (excluding Recycle Bin)...")
            st.session_state.scanner.inventory_files()
            
            total_files = len(st.session_state.scanner.file_inventory)
            status_text.text(f"🔍 Analyzing {total_files} files...")
            
            for i, _ in enumerate(st.session_state.scanner.process_files()):
                progress = min(i / max(total_files, 1), 1.0)
                progress_bar.progress(progress)
                status_text.text(f"📊 Processed {i+1} of {total_files} files...")
            
            progress_bar.progress(1.0)
            st.session_state.scan_results = st.session_state.scanner.get_duplicate_groups()
            st.session_state.scan_complete = True
            
            status_text.text(f"✅ Scan complete! Found {len(st.session_state.scan_results)} duplicate groups below.")
            st.rerun()
        else:
            st.error(f"❌ Directory '{scan_directory}' does not exist.")

with tab_organizer:
    st.markdown("""
    <div class="feature-card">
        <h3>📁 Smart File Organizer</h3>
        <p>Organize duplicate files into structured folders automatically</p>
    </div>
    """, unsafe_allow_html=True)
    
    if not st.session_state.scan_complete and not st.session_state.auto_scan_complete:
        st.info("🔍 Please complete a scan first in the Scanner tab or use Smart Scan.")
    else:
        organize_dir = st.text_input("📂 Organization Directory", 
                                    value=os.path.join(str(Path.home()), "DupliFinder_Organized"),
                                    help="Where to create organized folders")
        
        organize_option = st.radio(
            "📋 Organization Method",
            options=["Move duplicates to folders", "Copy duplicates to folders", "Just view plan"]
        )
        
        keep_original = st.checkbox("💾 Keep one file in original location", value=True)
        
        if st.button("🗂️ Organize Files", key="organize_files", type="primary"):
            if st.session_state.scan_results:
                organizer = FileOrganizer(
                    duplicate_groups=st.session_state.scan_results,
                    destination_dir=organize_dir,
                    keep_original=keep_original
                )
                
                organization_plan = organizer.generate_organization_plan()
                
                st.subheader("📋 Organization Plan")
                for group_name, files in organization_plan.items():
                    with st.expander(f"📁 {group_name} ({len(files)} files)"):
                        for f in files:
                            st.text(f"📄 {f['source']} → {f['destination']}")
                
                if organize_option != "Just view plan":
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    total_files = sum(len(files) for files in organization_plan.values())
                    processed = 0
                    
                    for group_name, files in organization_plan.items():
                        for file_info in files:
                            if organize_option == "Move duplicates to folders":
                                organizer.move_file(file_info["source"], file_info["destination"])
                            else:
                                organizer.copy_file(file_info["source"], file_info["destination"])
                            
                            processed += 1
                            progress = min(processed / total_files, 1.0)
                            progress_bar.progress(progress)
                            status_text.text(f"📊 Processed {processed} of {total_files} files...")
                    
                    progress_bar.progress(1.0)
                    status_text.text("✅ Organization complete!")
                    
                    summary = organizer.get_summary()
                    st.success(f"✅ Organized {summary['total_files']} files into {summary['total_groups']} groups.")

with tab_monitor:
    st.markdown("""
    <div class="feature-card">
        <h3>👁️ Real-time File Monitor</h3>
        <p>Monitor directories for new files and auto-organize duplicates</p>
    </div>
    """, unsafe_allow_html=True)
    
    monitor_directory = st.text_input("📂 Directory to Monitor", 
                                    value=str(Path.home() / "Downloads"))
    
    auto_organize = st.checkbox("🤖 Auto-organize duplicates", value=True)
    organize_path = st.text_input("📁 Auto-organize destination", 
                                 value=os.path.join(str(Path.home() / "Downloads"), "Auto_Organized"))
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶️ Start Monitoring", key="start_monitor", 
                    disabled=st.session_state.monitor_active, type="primary"):
            if os.path.exists(monitor_directory):
                st.session_state.monitor = FileMonitor(
                    directory=monitor_directory,
                    auto_organize=auto_organize,
                    organize_path=organize_path
                )
                st.session_state.monitor.start_monitoring()
                st.session_state.monitor_active = True
                st.rerun()
            else:
                st.error(f"❌ Directory '{monitor_directory}' does not exist.")
    
    with col2:
        if st.button("⏹️ Stop Monitoring", key="stop_monitor", 
                    disabled=not st.session_state.monitor_active):
            if st.session_state.monitor:
                st.session_state.monitor.stop_monitoring()
                st.session_state.monitor_active = False
                st.rerun()
    
    if st.session_state.monitor_active:
        st.success(f"✅ Monitoring active: {monitor_directory}")
        
        if st.session_state.monitor:
            log_data = st.session_state.monitor.get_activity_log()
            
            if log_data:
                st.subheader("📊 Activity Log")
                for entry in log_data[::-1][:10]:  # Show last 10 entries
                    st.text(f"🕒 {entry['timestamp']} - {entry['event']}")
            else:
                st.info("👁️ Monitoring active. No file events detected yet.")
    else:
        st.info("⏸️ Monitoring inactive. Click 'Start Monitoring' to begin.")

# Display scan results immediately after any scan
if st.session_state.scan_complete or st.session_state.auto_scan_complete:
    st.markdown("---")
    st.markdown("""
    <div class="feature-card">
        <h3>📊 Scan Results & File Actions</h3>
        <p>View and manage duplicate files organized in clear groups</p>
    </div>
    """, unsafe_allow_html=True)
    
    display_scan_results()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; padding: 2rem;">
    <h4>🤖 DupliFinder AI</h4>
    <p>Intelligent File Duplicate Detection & Organization System</p>
    <p>Made with ❤️ for efficient file management | Excludes Recycle Bin & System Folders</p>
</div>
""", unsafe_allow_html=True)