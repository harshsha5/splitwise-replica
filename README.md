# Expense Tracker

A Flask-based web application for tracking and splitting expenses among multiple participants.

## Features

- Add and manage expenses with multiple payers and participants
- Support for equal and unequal payment/split distributions
- Track net balances for users across all expenses
- Edit and delete existing expenses
- Clean web interface for expense management

## Setup Instructions

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Installation

1. Clone or navigate to the project directory:
   ```bash
   cd /path/to/splitwise-replica
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```

4. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Runtime Instructions

### Starting the Application

1. **Activate the virtual environment** (if not already active):
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     venv\Scripts\activate
     ```

2. **Run the application**:
   ```bash
   python app.py
   ```

3. **Access the application**:
   Open your web browser and navigate to: `http://127.0.0.1:5001`

### Using the Application

- **Home Page**: View all expenses and your current net balance
- **Add Expense**: Create new expenses with multiple payers and participants
- **View Expense**: See detailed breakdown of any expense
- **Edit Expense**: Modify existing expenses
- **Delete Expense**: Remove expenses from the system

### Stopping the Application

- Press `Ctrl+C` in the terminal to stop the Flask server
- Deactivate the virtual environment when done:
  ```bash
  deactivate
  ```

## Project Structure

- `app.py` - Main Flask application
- `models.py` - Data models for expenses and participants
- `requirements.txt` - Python dependencies
- `templates/` - HTML templates
- `static/` - CSS stylesheets
- `venv/` - Virtual environment (created during setup)

## Dependencies

- Flask 2.3.3 - Web framework
- Werkzeug 2.3.7 - WSGI utility library
- Jinja2 3.1.2 - Template engine