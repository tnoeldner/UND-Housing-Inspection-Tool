try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    
import json
import pandas as pd
from datetime import datetime
import streamlit as st

class InspectionDatabase:
    def __init__(self, connection_string=None):
        """
        Initialize database connection
        
        For SQL Server on campus network:
        connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=your-server;Database=Inspections;Trusted_Connection=yes;"
        
        For Azure SQL:
        connection_string = "Driver={ODBC Driver 17 for SQL Server};Server=tcp:yourserver.database.windows.net,1433;Database=Inspections;Uid=username;Pwd=password;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        """
        if not PYODBC_AVAILABLE:
            raise ImportError("pyodbc is not available. Please install with: pip install pyodbc")
        
        self.connection_string = connection_string or st.secrets.get("database", {}).get("connection_string", "")
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = pyodbc.connect(self.connection_string)
            return True
        except Exception as e:
            st.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def create_tables(self):
        """Create inspection tables if they don't exist"""
        if not self.connect():
            return False
        
        cursor = self.conn.cursor()
        
        try:
            # Main inspections table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Inspections' AND xtype='U')
                CREATE TABLE Inspections (
                    InspectionID INT IDENTITY(1,1) PRIMARY KEY,
                    InspectionType VARCHAR(50) NOT NULL,
                    Building VARCHAR(100) NOT NULL,
                    InspectionDate DATE NOT NULL,
                    Inspector VARCHAR(100) NOT NULL,
                    CreatedDate DATETIME DEFAULT GETDATE(),
                    AIReport NVARCHAR(MAX),
                    EmailReportHTML NVARCHAR(MAX),
                    SubmittedToSharePoint BIT DEFAULT 0
                )
            """)
            
            # Inspection details table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='InspectionDetails' AND xtype='U')
                CREATE TABLE InspectionDetails (
                    DetailID INT IDENTITY(1,1) PRIMARY KEY,
                    InspectionID INT NOT NULL,
                    Category VARCHAR(200),
                    Item VARCHAR(200) NOT NULL,
                    Rating VARCHAR(20),
                    Notes NVARCHAR(MAX),
                    FOREIGN KEY (InspectionID) REFERENCES Inspections(InspectionID)
                )
            """)
            
            # APPA scores summary table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='APPAScores' AND xtype='U')
                CREATE TABLE APPAScores (
                    ScoreID INT IDENTITY(1,1) PRIMARY KEY,
                    InspectionID INT NOT NULL,
                    OverallAPPALevel INT,
                    Level1Count INT DEFAULT 0,
                    Level2Count INT DEFAULT 0,
                    Level3Count INT DEFAULT 0,
                    Level4Count INT DEFAULT 0,
                    Level5Count INT DEFAULT 0,
                    FOREIGN KEY (InspectionID) REFERENCES Inspections(InspectionID)
                )
            """)
            
            self.conn.commit()
            st.success("Database tables created successfully!")
            return True
            
        except Exception as e:
            st.error(f"Error creating tables: {e}")
            return False
        finally:
            cursor.close()
            self.disconnect()
    
    def save_inspection(self, inspection_data):
        """Save inspection data to database"""
        if not self.connect():
            return False, "Database connection failed"
        
        cursor = self.conn.cursor()
        
        try:
            # Insert main inspection record
            cursor.execute("""
                INSERT INTO Inspections (InspectionType, Building, InspectionDate, Inspector, AIReport, EmailReportHTML)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                inspection_data['type'],
                inspection_data['building'],
                inspection_data['date'],
                inspection_data['inspector'],
                inspection_data.get('aiReport', ''),
                inspection_data.get('emailReportHTML', '')
            ))
            
            # Get the inspection ID
            cursor.execute("SELECT @@IDENTITY")
            inspection_id = cursor.fetchone()[0]
            
            # Insert inspection details
            level_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            
            for detail in inspection_data.get('details', []):
                cursor.execute("""
                    INSERT INTO InspectionDetails (InspectionID, Item, Rating, Notes)
                    VALUES (?, ?, ?, ?)
                """, (
                    inspection_id,
                    detail['item'],
                    detail['rating'],
                    detail.get('notes', '')
                ))
                
                # Count APPA levels
                if detail['rating'].startswith('Level '):
                    level = int(detail['rating'].split(' ')[1])
                    level_counts[level] += 1
            
            # Insert APPA scores summary
            cursor.execute("""
                INSERT INTO APPAScores (InspectionID, Level1Count, Level2Count, Level3Count, Level4Count, Level5Count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                inspection_id,
                level_counts[1], level_counts[2], level_counts[3], level_counts[4], level_counts[5]
            ))
            
            self.conn.commit()
            return True, f"Inspection saved with ID: {inspection_id}"
            
        except Exception as e:
            self.conn.rollback()
            return False, f"Error saving inspection: {e}"
        finally:
            cursor.close()
            self.disconnect()
    
    def get_inspections(self, limit=100, building=None, inspection_type=None, date_from=None, date_to=None):
        """Retrieve inspections with optional filtering"""
        if not self.connect():
            return []
        
        cursor = self.conn.cursor()
        
        try:
            query = """
                SELECT i.InspectionID, i.InspectionType, i.Building, i.InspectionDate, 
                       i.Inspector, i.CreatedDate, a.OverallAPPALevel,
                       a.Level1Count, a.Level2Count, a.Level3Count, a.Level4Count, a.Level5Count
                FROM Inspections i
                LEFT JOIN APPAScores a ON i.InspectionID = a.InspectionID
                WHERE 1=1
            """
            
            params = []
            
            if building:
                query += " AND i.Building = ?"
                params.append(building)
            
            if inspection_type:
                query += " AND i.InspectionType = ?"
                params.append(inspection_type)
            
            if date_from:
                query += " AND i.InspectionDate >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND i.InspectionDate <= ?"
                params.append(date_to)
            
            query += " ORDER BY i.CreatedDate DESC"
            
            if limit:
                query = f"SELECT TOP {limit} * FROM ({query}) AS limited_results"
            
            cursor.execute(query, params)
            
            columns = [column[0] for column in cursor.description]
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
            
        except Exception as e:
            st.error(f"Error retrieving inspections: {e}")
            return []
        finally:
            cursor.close()
            self.disconnect()
    
    def get_inspection_details(self, inspection_id):
        """Get detailed inspection data"""
        if not self.connect():
            return None
        
        cursor = self.conn.cursor()
        
        try:
            # Get main inspection info
            cursor.execute("""
                SELECT * FROM Inspections WHERE InspectionID = ?
            """, (inspection_id,))
            
            inspection = cursor.fetchone()
            if not inspection:
                return None
            
            # Convert to dict
            columns = [column[0] for column in cursor.description]
            inspection_dict = dict(zip(columns, inspection))
            
            # Get inspection details
            cursor.execute("""
                SELECT Item, Rating, Notes FROM InspectionDetails 
                WHERE InspectionID = ? ORDER BY DetailID
            """, (inspection_id,))
            
            details = []
            for row in cursor.fetchall():
                details.append({
                    'item': row[0],
                    'rating': row[1], 
                    'notes': row[2]
                })
            
            inspection_dict['details'] = details
            return inspection_dict
            
        except Exception as e:
            st.error(f"Error retrieving inspection details: {e}")
            return None
        finally:
            cursor.close()
            self.disconnect()
    
    def get_dashboard_data(self):
        """Get summary data for dashboard"""
        if not self.connect():
            return {}
        
        cursor = self.conn.cursor()
        
        try:
            # Total inspections
            cursor.execute("SELECT COUNT(*) FROM Inspections")
            total_inspections = cursor.fetchone()[0]
            
            # Inspections by type
            cursor.execute("""
                SELECT InspectionType, COUNT(*) as Count 
                FROM Inspections 
                GROUP BY InspectionType
            """)
            by_type = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Recent activity (last 30 days)
            cursor.execute("""
                SELECT COUNT(*) FROM Inspections 
                WHERE CreatedDate >= DATEADD(day, -30, GETDATE())
            """)
            recent_activity = cursor.fetchone()[0]
            
            # Top buildings by inspection count
            cursor.execute("""
                SELECT TOP 10 Building, COUNT(*) as Count 
                FROM Inspections 
                GROUP BY Building 
                ORDER BY Count DESC
            """)
            top_buildings = [(row[0], row[1]) for row in cursor.fetchall()]
            
            return {
                'total_inspections': total_inspections,
                'by_type': by_type,
                'recent_activity': recent_activity,
                'top_buildings': top_buildings
            }
            
        except Exception as e:
            st.error(f"Error retrieving dashboard data: {e}")
            return {}
        finally:
            cursor.close()
            self.disconnect()