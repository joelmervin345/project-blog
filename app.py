from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MySQL Database Connection
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            port=3306,
            database='blog',  
            user='root',
            password=''
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Home page - show blog posts
@app.route('/')
def index():
    connection = get_db_connection()
    posts = []
    
    if not connection:
        flash('Database connection failed. Please check MySQL service.', 'danger')
        return render_template('index.html', posts=[])
    
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT p.*, u.username FROM posts p JOIN users u ON p.user_id = u.id ORDER BY created_at DESC')
        posts = cursor.fetchall()
    except Error as e:
        flash(f'Error fetching posts: {str(e)}', 'danger')
    finally:
        if 'cursor' in locals():
            cursor.close()
        if connection.is_connected():
            connection.close()
    
    return render_template('index.html', posts=posts)

# Add a new blog post
@app.route('/create', methods=['GET', 'POST'])
def add_post():
    if 'user_id' not in session:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection failed. Please check MySQL service.', 'danger')
            return render_template('create.html')
        
        try:
            cursor = connection.cursor()
            cursor.execute('INSERT INTO posts (title, content, user_id) VALUES (%s, %s, %s)', 
                         (title, content, session['user_id']))
            connection.commit()
            flash('Post created successfully!', 'success')
            return redirect(url_for('index'))
        except Error as e:
            flash(f'Error creating post: {str(e)}', 'danger')
            return render_template('create.html')
        finally:
            if 'cursor' in locals():
                cursor.close()
            if connection.is_connected():
                connection.close()
    
    return render_template('create.html')

# User registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection failed. Please check MySQL service.', 'danger')
            return render_template('register.html')
        
        try:
            cursor = connection.cursor(dictionary=True)
            
            # Check if username already exists
            cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                flash('Username already exists. Please choose a different username.', 'danger')
                return render_template('register.html')
            
            # Check if email already exists
            cursor.execute('SELECT id FROM users WHERE email = %s', (email,))
            if cursor.fetchone():
                flash('Email already registered. Please use a different email.', 'danger')
                return render_template('register.html')
            
            # Create the user
            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)', 
                         (username, email, hashed_password))
            connection.commit()
            
            flash('Account created successfully. You can now log in.', 'success')
            return redirect(url_for('login'))
        except Error as e:
            flash(f'Registration failed: {str(e)}', 'danger')
            return render_template('register.html')
        finally:
            if 'cursor' in locals():
                cursor.close()
            if connection.is_connected():
                connection.close()
    
    return render_template('register.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = get_db_connection()
        if not connection:
            flash('Database connection failed. Please check MySQL service.', 'danger')
            return render_template('login.html')
        
        try:
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Logged in successfully.', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'danger')
        except Error as e:
            flash(f'Login failed: {str(e)}', 'danger')
        finally:
            if 'cursor' in locals():
                cursor.close()
            if connection.is_connected():
                connection.close()
    
    return render_template('login.html')

# User logout
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

# Delete a blog post
@app.route('/delete/<int:post_id>', methods=['POST'])
def delete_post(post_id):
    if 'user_id' not in session:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if not connection:
        flash('Database connection failed. Please check MySQL service.', 'danger')
        return redirect(url_for('index'))
    
    try:
        cursor = connection.cursor(dictionary=True)
        # First check if the post exists and belongs to the current user
        cursor.execute('SELECT user_id FROM posts WHERE id = %s', (post_id,))
        post = cursor.fetchone()
        
        if not post:
            flash('Post not found.', 'danger')
            return redirect(url_for('index'))
            
        if post['user_id'] != session['user_id']:
            flash('You can only delete your own posts.', 'danger')
            return redirect(url_for('index'))
            
        # Delete the post
        cursor.execute('DELETE FROM posts WHERE id = %s', (post_id,))
        connection.commit()
        flash('Post deleted successfully.', 'success')
        
    except Error as e:
        flash(f'Error deleting post: {str(e)}', 'danger')
    finally:
        if 'cursor' in locals():
            cursor.close()
        if connection.is_connected():
            connection.close()
    
    return redirect(url_for('index'))

# Edit a blog post
@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    if 'user_id' not in session:
        flash('You need to log in first.', 'danger')
        return redirect(url_for('login'))
    
    connection = get_db_connection()
    if not connection:
        flash('Database connection failed. Please check MySQL service.', 'danger')
        return redirect(url_for('index'))
    
    try:
        cursor = connection.cursor(dictionary=True)
        
        if request.method == 'GET':
            # Fetch the post to edit
            cursor.execute('SELECT * FROM posts WHERE id = %s', (post_id,))
            post = cursor.fetchone()
            
            if not post:
                flash('Post not found.', 'danger')
                return redirect(url_for('index'))
                
            if post['user_id'] != session['user_id']:
                flash('You can only edit your own posts.', 'danger')
                return redirect(url_for('index'))
                
            return render_template('edit.html', post=post)
            
        elif request.method == 'POST':
            # Update the post
            title = request.form['title']
            content = request.form['content']
            
            # Verify post ownership before updating
            cursor.execute('SELECT user_id FROM posts WHERE id = %s', (post_id,))
            post = cursor.fetchone()
            
            if not post:
                flash('Post not found.', 'danger')
                return redirect(url_for('index'))
                
            if post['user_id'] != session['user_id']:
                flash('You can only edit your own posts.', 'danger')
                return redirect(url_for('index'))
            
            cursor.execute('UPDATE posts SET title = %s, content = %s WHERE id = %s',
                         (title, content, post_id))
            connection.commit()
            flash('Post updated successfully.', 'success')
            return redirect(url_for('index'))
            
    except Error as e:
        flash(f'Error updating post: {str(e)}', 'danger')
    finally:
        if 'cursor' in locals():
            cursor.close()
        if connection.is_connected():
            connection.close()
    
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
