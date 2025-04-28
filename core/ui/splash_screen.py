#!/usr/bin/env python3
# NetSCAN - Splash Screen

from PySide6.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

from core.version import load_manifest

class SplashScreen(QSplashScreen):
    """Custom splash screen with progress bar and status messages."""
    
    def __init__(self):
        # Create a blank pixmap for the splash screen
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.white)
        
        super().__init__(pixmap)
        
        # Create a container widget for our custom content
        self.container = QWidget(self)
        self.container.setGeometry(0, 0, 400, 300)
        
        # Create layout
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        
        # Get version from manifest
        manifest = load_manifest()
        version = manifest.get("version_string", "Unknown")
        
        # Add title
        self.title = QLabel("netWORKS")
        self.title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        self.title.setFont(font)
        layout.addWidget(self.title)
        
        # Add version label
        self.version_label = QLabel(f"Version {version}")
        self.version_label.setAlignment(Qt.AlignCenter)
        version_font = QFont()
        version_font.setPointSize(10)
        self.version_label.setFont(version_font)
        self.version_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.version_label)
        
        # Add status message
        self.status = QLabel("Initializing...")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)
        
        # Add progress bar
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        layout.addWidget(self.progress)
        
        # Set window flags
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
    
    def update_progress(self, value, message):
        """Update the progress bar and status message.
        
        Args:
            value: int - Progress value (0-100)
            message: str - Status message to display
        """
        self.progress.setValue(value)
        self.status.setText(message)
        self.repaint()
    
    def drawContents(self, painter):
        """Override to draw custom content."""
        # Draw background
        painter.fillRect(self.rect(), QColor(255, 255, 255))
        
        # Draw border
        painter.setPen(QColor(200, 200, 200))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1)) 