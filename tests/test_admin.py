# tests/test_admin.py

from datetime import datetime, timedelta
from app.models import Class
import pytest

def login(client, email, password):
    """
    Helper function to log in a user via form-based login.
    """
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)

def logout(client):
    """
    Helper function to log out a user.
    """
    return client.get('/logout', follow_redirects=True)

def test_admin_access(client, app):
    """
    Test access to the admin panel.
    """
    # Log in as a regular user
    login_response = login(client, 'test1@example.com', 'password1')
    response = client.get('/admin', follow_redirects=True)

    # Since Flask-Login redirects unauthorized users, check for the flash message
    assert response.status_code == 200, "Expected status code 200 for redirect"
    assert 'Access denied. Administrator privileges required.' in response.data.decode('utf-8'), "Expected access denied message"

    logout(client)

    # Log in as an administrator
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Correct password
    response = client.get('/admin', follow_redirects=True)

    # Check for successful admin panel access
    assert response.status_code == 200, "Expected status code 200 for admin panel access"
    assert 'Admin Panel' in response.data.decode('utf-8'), "Expected 'Admin Panel' in response"

    logout(client)

def test_add_class(client, app):
    """
    Test adding a new class as an administrator.
    """
    # Log in as an administrator
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Correct password

    # Add a new class
    response = client.post('/admin/add_class', data={
        'name': 'New Class',
        'description': 'Description of the new class.',
        'schedule': (datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%d %H:%M'),
        'capacity': 10,
        'days_of_week': ['Monday', 'Wednesday'],  # Assuming the form expects a list
        'extra_info': 'Additional information.'
    }, follow_redirects=True)

    assert 'Class successfully added!' in response.data.decode('utf-8'), "Expected success message for adding class"

    # Check if the class is added in the database
    with app.app_context():
        new_class = Class.query.filter_by(name='New Class').first()
        assert new_class is not None, "New class not found in the database"

    logout(client)

def test_edit_class(client, app):
    """
    Test editing an existing class as an administrator.
    """
    # Log in as an administrator
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Correct password

    # Edit an existing class (assuming class_id=1 exists)
    response = client.post('/admin/edit_class/1', data={
        'name': 'Edited Class',
        'description': 'Updated description.',
        'schedule': (datetime.utcnow() + timedelta(days=3)).strftime('%Y-%m-%d %H:%M'),
        'capacity': 8,
        'days_of_week': ['Tuesday', 'Thursday'],  # Assuming the form expects a list
        'extra_info': 'Updated additional information.'
    }, follow_redirects=True)

    assert 'Class updated successfully!' in response.data.decode('utf-8'), "Expected success message for editing class"

    # Check changes in the database
    with app.app_context():
        edited_class = Class.query.get(1)
        assert edited_class.name == 'Edited Class', "Class name was not updated"
        assert edited_class.capacity == 8, "Class capacity was not updated"

    logout(client)

def test_delete_class(client, app):
    """
    Test deleting an existing class as an administrator.
    """
    # Log in as an administrator
    login_response = login(client, 'admin@example.com', 'adminpassword')  # Correct password

    # Delete an existing class (assuming class_id=2 exists and has no bookings)
    response = client.post('/admin/delete_class/2', follow_redirects=True)
    assert 'Class deleted successfully.' in response.data.decode('utf-8'), "Expected success message for deleting class"

    # Check deletion in the database
    with app.app_context():
        deleted_class = Class.query.get(2)
        assert deleted_class is None, "Class was not deleted from the database"

    logout(client)