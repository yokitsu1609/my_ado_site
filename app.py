import os
from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

#окружение
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'ado_fan_project_secure_key_123')

#база данных
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'ado_db'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )

#Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

#пользователь
class User(UserMixin):
    def __init__(self, id, username, is_admin):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, username, is_admin FROM users WHERE id = %s', (user_id,))
    user_data = cur.fetchone()
    cur.close(); conn.close()
    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

#авторизация

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO users (username, password, is_admin) VALUES (%s, %s, %s)', 
                        (username, password, False))
            conn.commit()
            flash('Регистрация успешна! Теперь войдите.')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Ошибка регистрации (возможно, имя занято)')
        finally:
            cur.close(); conn.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, username, is_admin FROM users WHERE username = %s AND password = %s', 
                    (username, password))
        user_data = cur.fetchone()
        cur.close(); conn.close()
        if user_data:
            user = User(user_data[0], user_data[1], user_data[2])
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

#НОВОСТИ

@app.route('/')
@app.route('/news')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT title, content, date, id FROM news ORDER BY date DESC;')
    news = cur.fetchall()
    cur.close(); conn.close()
    return render_template('index.html', news=news)

@app.route('/add_news', methods=['POST'])
@login_required
def add_news():
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    title, content = request.form['title'], request.form['content']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO news (title, content) VALUES (%s, %s)', (title, content))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('index'))

@app.route('/delete_news/<int:news_id>')
@login_required
def delete_news(news_id):
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM news WHERE title = (SELECT title FROM news ORDER BY date DESC OFFSET %s LIMIT 1)', (news_id,))
    conn.commit()
    cur.close(); conn.close()
    flash('Новость удалена')
    return redirect(url_for('index'))

#ОТЗЫВЫ

@app.route('/add_review', methods=['POST'])
@login_required
def add_review():
    text = request.form.get('text')
    if text:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO reviews (username, text) VALUES (%s, %s)', 
                    (current_user.username, text))
        conn.commit()
        cur.close(); conn.close()
    return redirect(url_for('index'))

@app.route('/delete_review/<int:review_id>')
@login_required
def delete_review(review_id):
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM reviews WHERE id = %s', (review_id,))
    conn.commit()
    cur.close(); conn.close()
    flash('Отзыв удален')
    return redirect(url_for('index'))

#ДИСКОГРАФИЯ

@app.route('/discography')
def discography():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, title, release_year, description, image_url FROM albums ORDER BY release_year DESC;')
    albums = cur.fetchall()
    cur.close(); conn.close()
    return render_template('discography.html', albums=albums)

@app.route('/add_album', methods=['POST'])
@login_required
def add_album():
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    title, year, desc, url = request.form['title'], request.form['year'], request.form['desc'], request.form['url']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO albums (title, release_year, description, image_url) VALUES (%s, %s, %s, %s)', 
                (title, year, desc, url))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('discography'))

@app.route('/album/<int:album_id>')
def album_page(album_id):
    conn = get_db_connection()
    cur = conn.cursor()
    
    #данные альбома
    cur.execute('SELECT title, image_url, description, id FROM albums WHERE id = %s', (album_id,))
    album = cur.fetchone()

    cur.execute('SELECT title, spotify_id, youtube_id, id FROM tracks WHERE album_id = %s', (album_id,))
    tracks = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return render_template('album_detail.html', album=album, tracks=tracks, album_id=album_id)

@app.route('/add_track/<int:album_id>', methods=['POST'])
@login_required
def add_track(album_id):
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    title = request.form.get('title')
    s_url = request.form.get('spotify_url', '')
    y_url = request.form.get('youtube_url', '')
    s_id = s_url.split('track/')[1].split('?')[0] if 'track/' in s_url else s_url
    y_id = ""
    if 'v=' in y_url: y_id = y_url.split('v=')[1].split('&')[0]
    elif 'youtu.be/' in y_url: y_id = y_url.split('youtu.be/')[1].split('?')[0]
    else: y_id = y_url

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO tracks (album_id, title, spotify_id, youtube_id) VALUES (%s, %s, %s, %s)',
                (album_id, title, s_id, y_id))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('album_page', album_id=album_id))



@app.route('/about')
def about():
    conn = get_db_connection()
    cur = conn.cursor()
    #комментарии для биографии
    cur.execute('SELECT username, text, date FROM about_comments ORDER BY date DESC;')
    comments = cur.fetchall()
    cur.close(); conn.close()
    return render_template('about.html', comments=comments)

@app.route('/add_about_comment', methods=['POST'])
@login_required
def add_about_comment():
    text = request.form.get('text')
    if text:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('INSERT INTO about_comments (username, text) VALUES (%s, %s)', 
                    (current_user.username, text))
        conn.commit()
        cur.close(); conn.close()
    return redirect(url_for('about'))


@app.route('/add_to_favorite', methods=['POST'])
@login_required
def add_to_favorite():
    content_id = request.form.get('content_id')
    content_type = request.form.get('content_type')
    title = request.form.get('title')
    extra_data = request.form.get('extra_data')

    conn = get_db_connection()
    cur = conn.cursor()
    
    #нет ли уже в избранном
    cur.execute('SELECT id FROM favorites WHERE user_id = %s AND content_id = %s AND content_type = %s',
                (current_user.id, content_id, content_type))
    
    if cur.fetchone():
        flash('Уже в избранном!')
    else:
        cur.execute('INSERT INTO favorites (user_id, content_id, content_type, title, extra_data) VALUES (%s, %s, %s, %s, %s)',
                    (current_user.id, content_id, content_type, title, extra_data))
        conn.commit()
        flash('Добавлено в любимое ❤️')
    
    cur.close(); conn.close()
    return redirect(request.referrer)

@app.route('/favorites')
@login_required
def favorites_page():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT content_type, title, extra_data, content_id FROM favorites WHERE user_id = %s ORDER BY date_added DESC', (current_user.id,))
    favs = cur.fetchall()
    cur.close(); conn.close()
    
    #категориям 
    fav_data = {
        'albums': [f for f in favs if f[0] == 'album'],
        'tracks': [f for f in favs if f[0] == 'track'],
        'videos': [f for f in favs if f[0] == 'video']
    }
    return render_template('favorites.html', favorites=fav_data)


@app.route('/concerts')
def concerts():
    conn = get_db_connection()
    cur = conn.cursor()
    #сортируя по дате
    cur.execute('SELECT id, city, venue, concert_date, ticket_url, is_sold_out FROM concerts ORDER BY concert_date ASC;')
    concerts_data = cur.fetchall()
    cur.close(); conn.close()
    return render_template('concerts.html', concerts=concerts_data)

@app.route('/add_concert', methods=['POST'])
@login_required
def add_concert():
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    
    city = request.form.get('city')
    venue = request.form.get('venue')
    date = request.form.get('date')
    url = request.form.get('url')
    
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('INSERT INTO concerts (city, venue, concert_date, ticket_url) VALUES (%s, %s, %s, %s)',
                (city, venue, date, url))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('concerts'))


@app.route('/site-info')
def site_info():
    return render_template('site_info.html')



@app.route('/home')
def home():
    conn = get_db_connection()
    cur = conn.cursor()
    # Берем отзывы
    cur.execute('SELECT username, text, date, id FROM reviews ORDER BY date DESC LIMIT 6;')
    reviews = cur.fetchall()
    cur.close(); conn.close()
    return render_template('home.html', reviews=reviews)



#УДАЛЕНИЯ ДЛЯ АДМИНА
@app.route('/delete_album/<int:album_id>', methods=['POST'])
@login_required
def delete_album(album_id):
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tracks WHERE album_id = %s', (album_id,))
    cur.execute('DELETE FROM albums WHERE id = %s', (album_id,))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('discography'))

@app.route('/delete_track/<int:track_id>', methods=['POST'])
@login_required
def delete_track(track_id):
    if not current_user.is_admin:
        return "Доступ запрещен", 403
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT album_id FROM tracks WHERE id = %s', (track_id,))
    res = cur.fetchone()
    album_id = res[0] if res else None
    cur.execute('DELETE FROM tracks WHERE id = %s', (track_id,))
    conn.commit()
    cur.close(); conn.close()
    return redirect(url_for('album_page', album_id=album_id))


if __name__ == '__main__':
    app.run(debug=True)