import datetime
from flask import Flask, render_template, request, session, url_for, flash, redirect, abort, g, make_response
from DataBaseAPI import DataBaseAPI
from flask_login import LoginManager, login_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from UserLogin import UserLogin

app = Flask(__name__)
app.config['SECRET_KEY'] = 'isaktimurov'
app.debug = True
app.config.from_object(__name__)
# app.config.update(dict(SQLALCHEMY_DATABASE_URI="sqlite:///sqlitedatabase.db"))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sqlitedatabase.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Вы не авторизованы!"
login_manager.login_message_category = "alert alert-danger"

dbase = DataBaseAPI(app)


@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id, dbase)


@app.route('/')
@login_required
def index():
    print(url_for('index'))
    return render_template('index.html', title='WEBUDGET')


@app.route("/login", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == "POST":
        user = dbase.getUserByUsername(request.form['username'])
        if user and check_password_hash(user['psw'], request.form['psw']):
            userlogin = UserLogin().create(user)
            rm = True if request.form.get('remainme') else False
            login_user(userlogin, remember=rm)
            return redirect(url_for('index'))

        flash("Неверная пара логин/пароль", category='alert alert-danger')

    return render_template('login.html', title='Вход в приложение')


@app.route("/add_paymentminus", methods=["POST", "GET"])
@login_required
def addPaymentminus():
    if request.method == "POST":
        if len(request.form['time']) > 0 and len(request.form['time']) > 0:
            res = dbase.addPost(current_user.get_id(), request.form['sum'], request.form['category'],
                                False, request.form['date'],
                                request.form['time'], request.form['message'])
            if not res:
                flash('Ошибка добавления статьи', category='error')
            else:
                flash('Статья добавлена успешно', category='success')
        else:
            flash('Неверно заполнены поля даты и времени', category='error')
    return render_template('add_paymentminus.html', title='Добавление расходов')


@app.route("/add_paymentplus", methods=["POST", "GET"])
@login_required
def addPaymentplus():
    if request.method == "POST":
        if len(request.form['time']) > 0 and len(request.form['time']) > 0:
            res = dbase.addPost(current_user.get_id(), request.form['sum'], "salary",
                                True, request.form['date'],
                                request.form['time'], request.form['message'])
            if not res:
                flash('Ошибка добавления статьи', category='error')
            else:
                flash('Статья добавлена успешно', category='success')
        else:
            flash('Неверно заполнены поля даты и времени', category='error')
    return render_template('add_paymentplus.html', title='Добавление доходов')


@app.route("/profile", methods=['POST', 'GET'])
@login_required
def profile():
    if request.method == 'POST':
        file = request.files['file']
        if file and verifyExt(file.filename):
            try:
                res = dbase.updateUserAvatar(file.read(), current_user.get_id())
                if not res:
                    flash("Ошибка обновления аватара", "alert alert-danger")
                flash("Аватар обновлен", "alert alert-success")
            except FileNotFoundError as e:
                flash("Ошибка чтения файла", "alert alert-danger")
        else:
            flash("Ошибка обновления аватара", "alert alert-danger")
    return render_template('profile.html', title='Профиль пользователя')


@app.route('/registration', methods=['POST', 'GET'])
def registration():
    if request.method == 'POST':
        if len(request.form['username']) > 4 and len(request.form['email']) > 4 and len(request.form['psw']) > 4 and \
                request.form['psw'] == request.form['psw2']:
            phash = generate_password_hash(request.form['psw'])
            res = dbase.addUser(request.form['username'], request.form['firstname'], request.form['email'], phash)
            if res:
                flash('Вы успешно зарегистрированы!', category='alert alert-success')
                return redirect(url_for('login'))
            else:
                flash('Ошибка при добавлении в базу данных.', category='alert alert-danger')
        else:
            flash('Неверно заполнены поля.', category='alert alert-danger')
    return render_template('registration.html', title='Регистрация')


@app.route('/contact', methods=['POST', 'GET'])
def contact():
    if request.method == 'POST':
        if len(request.form['username']) > 2:
            flash("Обращение успешно отправлено", category='alert alert-success')
            dbase.addFeedback(request.form['username'], request.form['email'], request.form['message'])
        else:
            flash('Ошибка! Обращение не отправлено ', category='alert alert-danger')

    return render_template('contact.html', title='Обратная связь')


@app.route('/history', methods=['POST', 'GET'])
@login_required
def history():
    date_from = ""
    date_to = ""
    try:
        date_from = request.args["date_from"]
    except:
        date_from = "0001-01-01"
    try:
        date_to = request.args["date_to"]
    except:
        date_to = "9000-01-01"
    raw_data = dbase.getDataBetween(int(current_user.get_id()), date_from, date_to)
    data = []
    if raw_data:
        for raw in raw_data:
            d = {}

            d["img"] = getIcon(raw.category)
            d["datetime"] = datetime.datetime.combine(raw.date, raw.time).strftime("%d.%m.%Y %H:%M")
            month = datetime.datetime.combine(raw.date, raw.time).strftime("%m")
            if month == '01':
                d["month"] = "января"
            elif month == '02':
                d["month"] = "февраля"
            elif month == '03':
                d["month"] = "марта"
            elif month == '04':
                d["month"] = "апреля"
            elif month == '05':
                d["month"] = "мая"
            elif month == '06':
                d["month"] = "июня"
            elif month == '07':
                d["month"] = "июля"
            elif month == '08':
                d["month"] = "августа"
            elif month == '09':
                d["month"] = "сентября"
            elif month == '10':
                d["month"] = "октября"
            elif month == '11':
                d["month"] = "ноября"
            elif month == '12':
                d["month"] = "декабря"
            if raw.type:
                d["type"] = "plusmon"
            else:
                d["type"] = "minusmon"
            if raw.type:
                d["amount"] = "+" + str(raw.amount) + "₽"
            else:
                d["amount"] = "-" + str(raw.amount) + "₽"
            data.append(d)
    return render_template('history.html', title='История операций', list=data[::-1])  # dbase.getData(current_user.get_id()))


@app.route('/statistics', methods=['POST', 'GET'])
@login_required
def statistics():
    dbase.getData(int(current_user.get_id()))
    return render_template('statistics.html', title='Статистика', list=dbase.getData(current_user.get_id()))


@app.route('/avatar')
def avatar():
    img = current_user.getAvatar(app)
    if not img:
        return ""
    h = make_response(img)
    h.headers['Content-Type'] = "image/jpg"
    return h


@app.route('/test', methods=['POST', 'GET'])
@login_required
def test():
    dbase.getData(int(current_user.get_id()))
    return render_template('test.html', title='TEST', list=dbase.getData(current_user.get_id()))


@app.errorhandler(404)
def pageNotFount(error):
    return render_template('page404.html'), 404


def verifyExt(filename):
    ext = filename.rsplit('.', 1)[1]
    if ext == "jpg" or ext == "JPG":
        return True
    return False


def getIcon(category):
    if category == "food":
        return "shopping_cart"
    if category == "study":
        return "local_library"
    if category == "cinema":
        return "movie"
    if category == "transport":
        return "directions_bus"
    if category == "transfer":
        return "transfer_within_a_station"
    if category == "salary":
        return "payment"
    return "payment"


if __name__ == '__main__':
    app.run(debug=True)
