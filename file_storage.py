import json
import os
import pandas as pd
from datetime import datetime
import streamlit as st

class FileStorage:
    """Simple file-based storage for inspections when database is not available"""
    
    def __init__(self, storage_dir="inspection_data"):
        self.storage_dir = storage_dir
        self.ensure_directory()
    
    def ensure_directory(self):
        """Create storage directory if it doesn't exist"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
    
    def save_inspection(self, inspection_data):
        """Save inspection data to JSON file"""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            building = inspection_data.get('building', 'Unknown').replace(' ', '_')
            inspection_type = inspection_data.get('type', 'unknown')
            
            filename = f"{timestamp}_{inspection_type}_{building}.json"
            filepath = os.path.join(self.storage_dir, filename)
            
            # Add metadata
            inspection_data['saved_at'] = datetime.now().isoformat()
            inspection_data['file_id'] = timestamp
            
            # Save to file
            with open(filepath, 'w') as f:
                json.dump(inspection_data, f, indent=2, default=str)
            
            return True, f"Inspection saved as {filename}"
            
        except Exception as e:
            return False, f"Error saving inspection: {e}"
    
    def get_inspections(self, limit=100):
        """Get list of saved inspections"""
        try:
            files = []
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(self.storage_dir, filename)
                    
                    # Get file info
                    stat = os.stat(filepath)
                    created = datetime.fromtimestamp(stat.st_ctime)
                    
                    # Try to load basic info
                    try:
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        
                        files.append({
                            'filename': filename,
                            'created': created,
                            'building': data.get('building', 'Unknown'),
                            'inspection_type': data.get('type', 'unknown'),
                            'inspector': data.get('inspector', 'Unknown'),
                            'date': data.get('date', 'Unknown')
                        })
                    except:
                        # Skip files that can't be read
                        continue
            
            # Sort by creation date (newest first) and limit
            files.sort(key=lambda x: x['created'], reverse=True)
            return files[:limit]
            
        except Exception as e:
            st.error(f"Error reading inspections: {e}")
            return []
    
    def get_inspection_data(self, filename):
        """Get full inspection data from file"""
        try:
            filepath = os.path.join(self.storage_dir, filename)
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error reading inspection file: {e}")
            return None
    
    def export_to_csv(self, output_file="inspections_export.csv"):
        """Export all inspections to CSV"""
        try:
            inspections = self.get_inspections(limit=None)
            all_data = []
            
            for inspection_info in inspections:
                data = self.get_inspection_data(inspection_info['filename'])
                if data:
                    # Flatten the data for CSV
                    row = {
                        'filename': inspection_info['filename'],
                        'building': data.get('building'),
                        'inspection_type': data.get('type'),
                        'inspector': data.get('inspector'),
                        'inspection_date': data.get('date'),
                        'saved_at': data.get('saved_at'),
                        'ai_report': data.get('aiReport', ''),
                        'total_items': len(data.get('details', []))
                    }
                    
                    # Count APPA levels
                    level_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
                    for detail in data.get('details', []):
                        if detail.get('rating', '').startswith('Level '):
                            try:
                                level = int(detail['rating'].split(' ')[1])
                                level_counts[level] += 1
                            except:
                                continue
                    
                    row.update({
                        'level_1_count': level_counts[1],
                        'level_2_count': level_counts[2],
                        'level_3_count': level_counts[3],
                        'level_4_count': level_counts[4],
                        'level_5_count': level_counts[5]
                    })
                    
                    all_data.append(row)
            
            # Create DataFrame and save
            df = pd.DataFrame(all_data)
            df.to_csv(output_file, index=False)
            
            return True, f"Exported {len(all_data)} inspections to {output_file}"
            
        except Exception as e:
            return False, f"Error exporting to CSV: {e}"
    
    def get_summary_stats(self):
        """Get summary statistics"""
        try:
            inspections = self.get_inspections(limit=None)
            
            if not inspections:
                return {}
            
            # Basic stats
            total = len(inspections)
            by_type = {}
            by_building = {}
            
            for inspection in inspections:
                # Count by type
                itype = inspection['inspection_type']
                by_type[itype] = by_type.get(itype, 0) + 1
                
                # Count by building
                building = inspection['building']
                by_building[building] = by_building.get(building, 0) + 1
            
            # Recent activity (last 30 days)
            recent_cutoff = datetime.now() - pd.Timedelta(days=30)
            recent = sum(1 for i in inspections if i['created'] >= recent_cutoff)
            
            return {
                'total_inspections': total,
                'by_type': by_type,
                'by_building': by_building,
                'recent_activity': recent,
                'storage_type': 'File-based'
            }
            
        except Exception as e:
            st.error(f"Error getting summary stats: {e}")
            return {}