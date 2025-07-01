# Legal Actions Dashboard

## Overview

This is a Dash-based web application that provides an interactive dashboard for tracking and analyzing legal actions against companies across different industries. The application features real-time filtering, data visualization with Plotly charts, and responsive data tables for detailed legal action records.

## System Architecture

### Backend Architecture
- **Framework**: Dash (Python interactive web framework)
- **Database ORM**: SQLAlchemy with Flask-SQLAlchemy extension
- **Database**: PostgreSQL (configured via environment variables)
- **WSGI Server**: Gunicorn serving the Dash Flask server
- **Interactive Components**: Native Dash callbacks for real-time updates

### Frontend Architecture
- **UI Framework**: Dash HTML/Core Components with Bootstrap styling
- **CSS Framework**: Bootstrap 5 with responsive design
- **Data Visualization**: Plotly for interactive charts and graphs
- **Data Tables**: Dash DataTable with built-in sorting and filtering
- **Real-time Updates**: Dash callbacks for interactive components

### Data Architecture
The application uses a relational database with three main entities:
- **Companies**: Stores company information
- **Industries**: Categorizes different industry types  
- **Legal Actions**: Central entity linking companies and industries with legal action details

## Key Components

### Database Models (`database.py`)
- **Company Model**: Stores company names with timestamps
- **Industry Model**: Categorizes business sectors  
- **LegalAction Model**: Central model containing legal action details, linked to companies and industries via foreign keys

### Dash Application (`dash_app.py`)
- **Interactive Components**: Dropdown filters, data tables, and charts
- **Callbacks**: Real-time updates when filters change
- **Database Integration**: Direct SQLAlchemy queries within callback functions
- **Plotly Visualizations**: Time-series charts with interactive features

### Application Structure
- **Main Entry Point** (`main.py`): Exposes Flask server for Gunicorn deployment
- **Database Setup** (`database.py`): Standalone database configuration avoiding circular imports
- **Dashboard Logic** (`dash_app.py`): Complete Dash application with UI and callbacks

## Data Flow

1. **Initial Load**: Dashboard loads filter options and data directly from database via Dash callbacks
2. **User Interaction**: Filter selections trigger Dash callback functions automatically
3. **Data Processing**: Backend queries PostgreSQL database with applied filters using SQLAlchemy
4. **Visualization Update**: Dash callbacks update Plotly charts and DataTable components in real-time
5. **Real-time Updates**: Native Dash reactivity handles component updates without page refresh

## External Dependencies

### Python Dependencies
- **Dash**: Interactive web framework for Python applications
- **Dash Bootstrap Components**: Bootstrap-styled components for Dash
- **Plotly**: Interactive data visualization library
- **Pandas**: Data manipulation and analysis library
- **NumPy**: Numerical computing foundation
- **SQLAlchemy**: Database ORM and query builder
- **Flask-SQLAlchemy**: SQLAlchemy integration (used by Dash's Flask server)
- **Gunicorn**: Production WSGI server
- **psycopg2-binary**: PostgreSQL database adapter

### Frontend Dependencies (Included with Dash)
- **Bootstrap 5**: UI framework styling
- **Plotly.js**: Interactive visualization engine
- **React**: Component framework underlying Dash components

## Deployment Strategy

### Development Environment
- Uses Dash's built-in development server with Flask backend
- Debug mode enabled for development with auto-reload
- Database tables created automatically on startup

### Production Environment
- **WSGI Server**: Gunicorn serving Dash's Flask server
- **Process Management**: Configured for 0.0.0.0:5000 binding
- **Load Balancing**: Supports port reuse and auto-reload
- **Interactive Components**: Real-time updates via Dash callbacks

### Environment Configuration
- Database connection via `DATABASE_URL` environment variable
- Session security via `SESSION_SECRET` environment variable
- Connection pooling with 300-second recycle time and pre-ping validation

## Changelog

```
Changelog:
- June 26, 2025: Initial Flask setup with PostgreSQL integration
- June 26, 2025: Converted from Flask to Dash framework
- June 26, 2025: Updated project dependencies to focus on Dash components
- June 26, 2025: Populated database with 25 legal action records across 10 companies and 10 industries
- June 26, 2025: Cleaned up project structure - removed unused Flask files (models.py, app.py, routes.py, templates/, static/)
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```