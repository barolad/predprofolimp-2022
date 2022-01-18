import sqlite3
import os
from flask import Flask, render_template, request, session, url_for, flash, redirect, abort, g
from FDataBase import FDataBase
from flask_login import LoginManager, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from UserLogin import UserLogin

DATABASE = '/tmp/database.db'
DEBUG = True
SECRET_KEY = 'ee71d2fce7f1013378f6f73e1bc144020934702c'
MAX_CONTENT_LENGTH = 1024 * 1024

app = Flask(__name__)
app.config['SECRET_KEY']='isaktimurov'
app.config.from_object(__name__)
app.config.update(dict(DATABASE=os.path.join(app.root_path,'database.db')))

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Вы не авторизованы!"
login_manager.login_message_category = "alert alert-danger"


@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id, dbase)


def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def create_db():
    """Вспомогательная функция для создания таблиц БД"""
    db = connect_db()
    with app.open_resource('sq_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


def get_db():
    '''Соединение с БД, если оно еще не установлено'''
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db


@app.teardown_appcontext
def close_db(error):
    '''Закрываем соединение с БД, если оно было установлено'''
    if hasattr(g, 'link_db'):
        g.link_db.close()


dbase = None
@app.before_request
def before_request():
    """Установление соединения с БД перед выполнением запроса"""
    global dbase
    db = get_db()
    dbase = FDataBase(db)


@app.route('/')
@login_required
def index():
    db=get_db()
    dbase=FDataBase(db)
    print(url_for('index'))
    return render_template('index.html')


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method=="POST":
        user=dbase.getUserByUsername(request.form['username'])
        if user and check_password_hash(user['psw'], request.form['psw']):
            userlogin = UserLogin().create(user)
            rm = True if request.form.get('remainme') else False
            login_user(userlogin, remember=rm)
            return redirect(url_for('index'))

        flash("Неверная пара логин/пароль", category='alert alert-danger')
 
    return render_template('login.html')


@app.route("/add_payment")
def addPayment():
    if request.method == "POST":
        if len(request.form['name']) > 4 and len(request.form['post']) > 10:
            res = dbase.addPost(request.form['name'], request.form['post'], request.form['url'])
            if not res:
                flash('Ошибка добавления статьи', category = 'error')
            else:
                flash('Статья добавлена успешно', category='success')
        else:
            flash('Ошибка добавления статьи', category='error')
    return render_template('add_payment.html')


@app.route("/profile")
def profile():
    return render_template('contact.html')


@app.route('/registration', methods=['POST','GET'])
def registration():
    if request.method == 'POST':
        if (len(request.form['username'])>4 and len(request.form['email'])>4 and len(request.form['psw'])>4 and request.form['psw']==request.form['psw2']):
            hash=generate_password_hash(request.form['psw'])
            res=dbase.addUser(request.form['username'],request.form['firstname'],request.form['email'], hash)
            if res:
                flash('Вы успешно зарегистрированы!', category='alert alert-success')
                return redirect(url_for('login'))
            else:
                flash('Ошибка при добавлении в базу данных.', category='alert alert-danger')
        else:
            flash('Неаверно заполнены поля.', category='alert alert-danger')
    return render_template('registration.html')


@app.route('/contact', methods=['POST','GET'])
def contact():
    if request.method=='POST':
        print(request.form)
        if len(request.form['username'])>2:
            flash("Обращение успешно отправлено", category='alert alert-success')
        else:
            flash('Ошибка! Обращение не отправлено ', category='alert alert-danger')
    print(url_for('contact'))
    return render_template('contact.html')


@app.errorhandler(404)
def pageNotFount(error):
    return render_template('page404.html'), 404


if __name__ == '__main__':
    app.run(debug=True)