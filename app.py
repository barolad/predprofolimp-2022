import datetime
import tempfile
from itertools import groupby

from flask import Flask, render_template, request, session, url_for, flash, redirect, abort, g, make_response
from DataBaseAPI import DataBaseAPI
from flask_login import LoginManager, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from UserLogin import UserLogin
import requests
from bs4 import BeautifulSoup as BS
import csv

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


@app.route('/', methods=["POST", "GET"])
@login_required
def index():
    # Парсинг инфы с сайта центробанка
    r = requests.get('http://www.cbr.ru/')
    html = BS(r.content, 'html.parser')
    O = []

    for el in html.select('.main-indicator'):
        title = el.select('.main-indicator_value')
        title = (title[0].text).split('%')
        title.pop(1)
        O.append(title)
    inf_future = str(O[0])[2:-2]
    inf_now = str(O[1])[2:-2]
    date = datetime.date.today()
    month_list = ['', 'январе', 'феврале', 'марте', 'апреле', 'мае', 'июне',
                  'июле', 'августе', 'сентябре', 'октябре', 'ноябре', 'декабре']
    currentmonth = month_list[date.month]
    return render_template('index.html', title='WEBUDGET', inf_future=inf_future, inf_now=inf_now,
                           currentmonth=currentmonth)


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
                flash('Ошибка добавления статьи', category='alert alert-danger')
            else:
                flash('Статья добавлена успешно', category='alert alert-success')
        else:
            flash('Неверно заполнены поля даты и времени', category='alert alert-danger')
    return render_template('add_paymentminus.html', title='Добавление расходов')


@app.route("/add_paymentplus", methods=["POST", "GET"])
@login_required
def addPaymentplus():
    if request.method == "POST":
        if len(request.form['time']) > 0 and len(request.form['time']) > 0:
            res = dbase.addPost(current_user.get_id(), request.form['sum'], request.form['category'],
                                True, request.form['date'],
                                request.form['time'], request.form['message'])
            if not res:
                flash('Ошибка добавления статьи', category='alert alert-danger')
            else:
                flash('Статья добавлена успешно', category='alert alert-success')
        else:
            flash('Неверно заполнены поля даты и времени', category='alert alert-danger')
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
    categories = []
    lenlist = 0
    currentyyear = ''
    try:
        base=request.args["base_product"]
    except:
        base="default"
    try:
        date_from = request.args["date_from"]
    except:
        date_from = "0001-01-01"
    if(date_from==""):
        date_from = "0001-01-01"
    try:
        date_to = request.args["date_to"]
    except:
        date_to = "9000-01-01"
    if(date_to==""):
        date_to = "9000-01-01"
    categories = request.args.getlist("category")
    if (len(categories) == 0):
        categories = ["m1", "m2", "m3", "m4", "m5", "m6", "m7", "m8", "m9", "m10", "m11", "m12", "p1", "p2", "p3", "p4",
                      "p5"]

    raw_data = dbase.getDataBetweenWithCategory(int(current_user.get_id()), date_from, date_to, categories)
    data = []
    data_to_export = []
    if raw_data:
        for raw in raw_data:
            d = {}
            d_e = {}
            d["img"] = getIcon(raw.category)
            d_e["category"] = getCategoryName(raw.category)
            d["description"] = raw.description
            d_e["description"] = raw.description
            d["datetime"] = datetime.datetime.combine(raw.date, raw.time).strftime("%d.%m.%Y %H:%M")
            d_e["date"] = datetime.datetime.combine(raw.date, raw.time).strftime("%d.%m.%Y")
            d_e["time"] = datetime.datetime.combine(raw.date, raw.time).strftime("%H:%M")
            month = datetime.datetime.combine(raw.date, raw.time).strftime("%m")
            d["month"] = getMonthName(month)
            if raw.type:
                d["type"] = "plusmon"
            else:
                d["type"] = "minusmon"
            if raw.type:
                d["amount"] = "+" + str(round(raw.amount/getBaseCost(base),2))+ " " + getBaseName(base)
            else:
                d["amount"] = "-" + str(round(raw.amount/getBaseCost(base),2)) + " " + getBaseName(base)
            if raw.type:
                d_e["amount"] = "+" + str(round(raw.amount/getBaseCost(base),2)) + " " + getBaseName(base)
            else:
                d_e["amount"] = "-" + str(round(raw.amount/getBaseCost(base),2)) + " " + getBaseName(base)
            data.append(d)
            data_to_export.append(d_e)
            lenlist = len(data)
            date = datetime.date.today()
            currentyyear = date.strftime("%Y")
    csvf_name = app.root_path
    csvf = open(csvf_name + "/static/export_" + current_user.getName() + ".csv", "w")
    writer = csv.DictWriter(csvf, fieldnames=["date", "time", "category", "description", "amount"], delimiter=';')
    writer.writerow(
        {"date": "Дата", "time": "Время", "category": "Категория", "description": "Описание", "amount": "Сумма"})
    writer.writerows(data_to_export[::-1])
    csvf.close()
    return render_template('history.html', title='История операций', list=data[::-1], lenlist=lenlist,
                           currentyear=currentyyear, login=current_user.getName())


@app.route('/statistics', methods=['POST', 'GET'])
@login_required
def statistics():
    data = []
    days_in_month_end = []
    date = datetime.date.today()
    days_in_month_list = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    days_in_month = days_in_month_list[date.month]
    date_from = "2022-02-01"
    date_to = "2022-03-01"
    currentmonth = getMonthNameImP(date.strftime("%m"))
    amountminusass, amountplusass, datplusass, datminusass = [], [], [], []
    raw_data = dbase.getDataBetween(int(current_user.get_id()), date_from, date_to)
    for i in range(1, days_in_month + 1):
        days_in_month_end.append(i)
    data_start_plus = [0] + [0] * len(days_in_month_end)
    data_start_minus = [0] + [0] * len(days_in_month_end)
    if raw_data:
        for raw in raw_data:
            if raw.type:
                datplusass.append(int(datetime.datetime.combine(raw.date, raw.time).strftime("%d")))
                hoplus = []
                for i in range(len(datplusass)):
                    hoplus.append(raw.amount)
                amountplusass.append(int(float(str([el for el, _ in groupby(hoplus)])[1:-1])))
            elif not (raw.type):
                datminusass.append(int(datetime.datetime.combine(raw.date, raw.time).strftime("%d")))
                hominus = []
                for i in range(len(datminusass)):
                    hominus.append(raw.amount)
                amountminusass.append(int(float(str([el for el, _ in groupby(hominus)])[1:-1])))
    dataplus = sorted(set(datplusass))
    dataminus = sorted(set(datminusass))
    amountplus = [0] * len(dataplus)
    amountminus = [0] * len(dataminus)
    for x in range(len(datplusass)):
        for i in range(len(dataplus)):
            if datplusass[x] == dataplus[i]:
                amountplus[i] += amountplusass[x]
    for x in range(len(datminusass)):
        for i in range(len(dataminus)):
            if datminusass[x] == dataminus[i]:
                amountminus[i] += amountminusass[x]
    for i in range(1, len(data_start_plus)):
        for j in range(len(dataplus)):
            if i == dataplus[j]:
                data_start_plus[i] = amountplus[j]
    for i in range(1, len(data_start_minus)):
        for j in range(len(dataminus)):
            if i == dataminus[j]:
                data_start_minus[i] = amountminus[j]
    # days_in_month_end[0]="01.02"
    return render_template('statistics.html', title='Статистика', currentmonth=currentmonth,
                           days_in_month_end=days_in_month_end, data_start_plus=data_start_plus,
                           data_start_minus=data_start_minus)


@app.route('/avatar')
@login_required
def avatar():
    img = current_user.getAvatar(app)
    if not img:
        return ""
    h = make_response(img)
    h.headers['Content-Type'] = "image/jpg"
    return h


@app.route('/history_export')
@login_required
def history_export():
    img = current_user.getAvatar(app)
    if not img:
        return ""
    h = make_response(img)
    h.headers['Content-Type'] = "text/csv"
    return h


@app.route('/test', methods=['POST', 'GET'])
@login_required
def test():
    dbase.getData(int(current_user.get_id()))
    return render_template('test.html', title='TEST', list=dbase.getData(current_user.get_id()))


@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash("Вы успешно вышли из аккаунта!", category='alert alert-success')
    return redirect(url_for('login'))


@app.errorhandler(404)
def pageNotFount(error):
    return render_template('page404.html'), 404


def verifyExt(filename):
    ext = filename.rsplit('.', 1)[1]
    if ext == "jpg" or ext == "JPG":
        return True
    return False


def getIcon(category):
    if category == "m1":
        return "restaurant"
    if category == "m2":
        return "handyman"
    if category == "m3":
        return "cable"
    if category == "m4":
        return "brush"
    if category == "m5":
        return "checkroom"
    if category == "m6":
        return "local_florist"
    if category == "m7":
        return "menu_book"
    if category == "m8":
        return "directions_car"
    if category == "m9":
        return "self_improvement"
    if category == "m10":
        return "local_cafe"
    if category == "m11":
        return "photo_size_select_actual"
    if category == "m12":
        return "payment"
    return "payment"


def getCategoryName(category):
    pass
    if category == "m1":
        return "Еда и продукты"
    if category == "m2":
        return "Дом и ремонт"
    if category == "m3":
        return "Электроника"
    if category == "m4":
        return "Хобби и развлечения"
    if category == "m5":
        return "Одежда, обувь, аксессуары"
    if category == "m6":
        return "Цветы и подарки"
    if category == "m7":
        return "Обучение"
    if category == "m8":
        return "Авто"
    if category == "m9":
        return "Уход за собой"
    if category == "m10":
        return "Кафе, бары и рестораны"
    if category == "m11":
        return "Книги, кино, искусство"
    if category == "p1":
        return "Зарплата"
    if category == "p2":
        return "Дивиденды"
    if category == "p3":
        return "Социальное пособие"
    if category == "p4":
        return "Перевод"
    if category == "p5":
        return "Возврат"
    return "Другое"


def getMonthNameImP(month):
    if month == '01':
        return "январь"
    elif month == '02':
        return "февраль"
    elif month == '03':
        return "март"
    elif month == '04':
        return "апрель"
    elif month == '05':
        return "май"
    elif month == '06':
        return "июнь"
    elif month == '07':
        return "июль"
    elif month == '08':
        return "август"
    elif month == '09':
        return "сентябрь"
    elif month == '10':
        return "октябрь"
    elif month == '11':
        return "ноябрь"
    elif month == '12':
        return "декабрь"


def getMonthName(month):
    if month == '01':
        return "января"
    elif month == '02':
        return "февраля"
    elif month == '03':
        return "марта"
    elif month == '04':
        return "апреля"
    elif month == '05':
        return "мая"
    elif month == '06':
        return "июня"
    elif month == '07':
        return "июля"
    elif month == '08':
        return "августа"
    elif month == '09':
        return "сентября"
    elif month == '10':
        return "октября"
    elif month == '11':
        return "ноября"
    elif month == '12':
        return "декабря"


def getBaseCost(name):
    if name == "donut":
        return 30
    if name == "BigMac":
        return 140
    if name == "Bus":
        return 50
    if name == "Taxi":
        return 200
    if name == "default":
        return 1


def getBaseName(name):
    if name == "donut":
        return "понч."
    if name == "BigMac":
        return "б.м."
    if name == "Bus":
        return "автоб."
    if name == "Taxi":
        return "такс."
    if name == "default":
        return "руб."


if __name__ == '__main__':
    app.run(debug=True)
