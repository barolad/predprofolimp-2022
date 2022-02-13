from flask import flash
from sqlalchemy import create_engine, MetaData, Table, String, Integer, Column, Text, DateTime, Boolean, BLOB, select, \
    insert, BINARY, update, Float, Date, Time, between
from flask_sqlalchemy import SQLAlchemy
import datetime
import pymysql
from werkzeug.security import check_password_hash

pymysql.install_as_MySQLdb()
now = datetime.datetime.now()


class DataBaseAPI:
    def __init__(self, app):
        self.__engine = SQLAlchemy(app).engine
        self.__connection = self.__engine.connect()
        self.__metadata = MetaData()
        self.setupTables()

    def setupTables(self):
        self.__users_table = Table('users', self.__metadata,
                                   Column('id', Integer(), primary_key=True, autoincrement=True),
                                   Column('username', Text(), primary_key=False, nullable=False),
                                   Column('firstname', Text(), primary_key=False, nullable=False),
                                   Column('email', Text(), primary_key=False, nullable=False),
                                   Column('psw', Text(), primary_key=False, nullable=False),
                                   Column('avatar', BLOB(), primary_key=False, default=None),
                                   Column('time', Text(), primary_key=False, nullable=False),
                                   )
        self.__user_data_table = Table('user_data', self.__metadata,
                                       Column('id', Integer(), primary_key=True, autoincrement=True),
                                       Column('user_id', Integer(), primary_key=False, nullable=False),
                                       Column('amount', Float(), primary_key=False, nullable=False),
                                       Column('category', Integer(), primary_key=False, nullable=False),
                                       Column('type', Boolean(), primary_key=False, nullable=False), #0 - расходы, 1 - доходы
                                       Column('description', Text(), primary_key=False, nullable=False),
                                       Column('time', Time(), primary_key=False, nullable=False),
                                       Column('date', Date(), primary_key=False, nullable=False)
                                       )
        self.__feedback_table = Table('feedback', self.__metadata,
                                      Column('id', Integer(), primary_key=True, autoincrement=True),
                                      Column('username', Text(), primary_key=False, nullable=False),
                                      Column('email', Text(), primary_key=False, nullable=False),
                                      Column('text', Text(), primary_key=False, nullable=False),
                                      Column('time', Text(), primary_key=False, nullable=False),
                                      )
        self.__metadata.create_all(self.__engine)

    def addUser(self, username, firstname, email, hpsw):
        try:
            select_query_email = select([self.__users_table]).where(
                self.__users_table.c.email == email
            )
            check_email = self.__connection.execute(select_query_email).rowcount <= 0
            if not check_email:
                flash("Пользователь с таким email уже существует")
                return False
            select_query_username = select([self.__users_table]).where(
                self.__users_table.c.username == username
            )
            check_username = self.__connection.execute(select_query_username).rowcount <= 0
            if not check_username:
                flash("Пользователь с таким логином уже существует")
                return False
            timestamp = now.strftime("%d-%m-%Y %H:%M")
            insert_query = insert(self.__users_table).values(
                username=username,
                firstname=firstname,
                email=email,
                psw=hpsw,
                time=timestamp
            )
            self.__connection.execute(insert_query)
        except BaseException as e:
            print("Ошибка добавления пользователя в БД " + str(e))
            return False
        return True

    def getUser(self, user_id):
        try:
            select_query = select([self.__users_table]).where(
                self.__users_table.c.id == user_id
            )
            select_result = self.__connection.execute(select_query).fetchone()
            if select_result is None:
                flash("Пользователь не найден", category='alert alert-danger')
                return False
            # if select_result["psw"] != hpsw:
            #    flash("Попытка взлома: ошибка при сверении хэшей паролей")
            #    return False
            output = dict(select_result)
            # del output["psw"]
            return output
        except BaseException as e:
            print("Ошибка получения данных из БД " + str(e))
            return False
        return True

    def getUserByUsername(self, username):
        try:
            select_query = select([self.__users_table]).where(
                self.__users_table.c.username == username
            )
            select_result = self.__connection.execute(select_query).fetchone()
            if select_result is None:
                flash("Пользователь не найден", category='alert alert-danger')
                return False
            # if select_result["psw"] != hpsw:
            #    flash("Попытка взлома: ошибка при сверении хэшей паролей")
            #    return False
            output = dict(select_result)
            # del output["psw"]
            return output
        except BaseException as e:
            print("Ошибка получения данных из БД " + str(e))
            return False
        return True

    def updateUserAvatar(self, avatar, user_id):
        if not avatar:
            return False
        try:
            select_query = select([self.__users_table]).where(
                self.__users_table.c.id == user_id
            )
            select_result = self.__connection.execute(select_query).fetchone()
            if select_result is None:
                flash("Пользователь не найден", category='alert alert-danger')
                return False
            # if select_result["psw"] != hpsw:
            #    flash("Попытка взлома: ошибка при сверении хэшей паролей")
            #    return False
            update_query = update(self.__users_table).where(
                self.__users_table.c.id == user_id
            ).values(
                avatar=avatar
            )
            self.__connection.execute(update_query)
        except BaseException as e:
            print("Ошибка обновления аватара в БД: " + str(e))
            return False
        return True

    def addFeedback(self, username, email, text):
        try:
            timestamp = now.strftime("%d-%m-%Y %H:%M")
            insert_query = insert(self.__feedback_table).values(
                username=username,
                email=email,
                text=text,
                time=timestamp
            )
            self.__connection.execute(insert_query)
        except BaseException as e:
            print("Ошибка отправки сообщения " + str(e))
            return False
        return True

    def addPost(self, user_id, summ, category, type, date, time, message):
        print(time,date)
        try:
            insert_query = insert(self.__user_data_table).values(
                user_id=int(user_id),
                amount=float(summ),
                category=category,
                description=message,
                type=type,
                time=datetime.datetime.strptime(time,"%H:%M").time(),
                date=datetime.datetime.strptime(date,"%Y-%m-%d").date()
            )
            self.__connection.execute(insert_query)
        except BaseException as e:
            print("Ошибка добавления записи" + str(e))
            return False
        return True
        pass

    def getData(self, user_id):
        try:
            select_query = select([self.__user_data_table]).where(
                self.__user_data_table.c.user_id == user_id
            )
            select_result = self.__connection.execute(select_query)
            if select_result is None:
                flash("Пользователь не найден", category='alert alert-danger')
                return False
            return select_result
        except BaseException as e:
            print("Ошибка добавления записи" + str(e))
            return False
        return True
        pass

    def getDataBetween(self, user_id,date_from,date_to):
        try:
            date_from_p=datetime.datetime.strptime(date_from,"%Y-%m-%d").date()
            date_to_p = datetime.datetime.strptime(date_to, "%Y-%m-%d").date()
            select_query = select([self.__user_data_table]).where(
                self.__user_data_table.c.user_id == user_id
            ).where(
                between(self.__user_data_table.c.date,date_from_p,date_to_p)
            )
            select_result = self.__connection.execute(select_query)
            if select_result is None:
                flash("Пользователь не найден", category='alert alert-danger')
                return False
            return select_result
        except BaseException as e:
            print("Ошибка добавления записи" + str(e))
            return False
        return True
        pass
