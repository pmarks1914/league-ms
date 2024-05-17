
from asyncio.log import logger
import email
from enum import unique
import hashlib
from locale import currency
import re
from textwrap import indent
from time import timezone
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import defer, undefer, relationship, load_only, sessionmaker
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from Helper.helper import generate_transaction_referance
from Settings import app
from datetime import datetime, timedelta
# from flask_script import Manager
from flask_migrate import Migrate
import json
# from sendEmail import Email 
from sqlalchemy import ForeignKey
import uuid
from sqlalchemy.ext.declarative import DeclarativeMeta

db = SQLAlchemy(app)
migrate = Migrate(app, db)

list_account_status = ['PENDING', 'APPROVED', 'REJECTED']
list_status = ['PENDING', 'SUCCESSFULL', 'FAILED']

def alchemy_to_json(obj, visited=None):
    if visited is None:
        visited = set()
    if obj in visited:
        return None  # Prevent infinite recursion
    visited.add(obj)
    if isinstance(obj.__class__, DeclarativeMeta):
        fields = {}
        exclude_fields = ["query", "registry", "query_class", "password", "apikey", "business"]
        for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata' and x not in exclude_fields]:
            data = obj.__getattribute__(field)
            try:
                if not callable(data):
                    # Check if the attribute is an instance of a SQLAlchemy model                    
                    if isinstance(data.__class__, DeclarativeMeta):
                        # Handle file relationship
                        fields[field] = alchemy_to_json(data, visited)
                    elif isinstance(data, list) and data and isinstance(data[0].__class__, DeclarativeMeta):
                        # Handle nested objects
                        fields[field] = [alchemy_to_json(item, visited) for item in data]
                    else:
                        # this will fail on non-encodable values, like other classes
                        json.dumps(data)
                        fields[field] = data
                else:
                    pass
            except TypeError:
                fields[field] = str(data)
        return fields

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    other_name = db.Column(db.String(80), nullable=True)
    active_status = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    school = db.relationship('School', back_populates='user')
    student = db.relationship('Student', back_populates='user')
    file = db.relationship('Fileupload', back_populates='user')
    
    def json(self):
        return {
                'id': self.id,
                'email': self.email,
                'role': self.role,
                'phone': self.phone, 
                'first_name': self.first_name, 
                'last_name': self.last_name, 
                'other_name': self.other_name, 
                'logo': self.logo, 
                'account_type': self.account_type, 
                'created_by': self.created_by,
                'updated_by': self.updated_by,
                'business_id': self.business_id, 
                'created_on': self.created_on,
                'updated_on': self.updated_on }
    def _repr_(self):
        return json.dumps({
                'id': self.id,
                'email': self.email,
                'role': self.role,
                'phone': self.phone, 
                'first_name': self.first_name, 
                'last_name': self.last_name, 
                'other_name': self.other_name, 
                'logo': self.logo, 
                'account_type': self.account_type, 
                'created_by': self.created_by,
                'updated_by': self.updated_by,
                'business_id': self.business_id, 
                'created_on': self.created_on,
                'updated_on': self.updated_on })

    def getUserById(id):
        new_data = User.query.filter_by(id=id).first()
        new_data_object = alchemy_to_json(new_data)
        return new_data_object

    def getAllUsers(_email):
        joined_table_data = []
        # user_data = db.session.query(User).filter_by(email=_email).join(Business).all()
        # user_data = db.session.query(User, Business).filter_by(email=_email).join(Business).all()
        user_data = db.session.query(User).filter_by(email=_email).all()

        # get joined tables data .
        for user in user_data:
            joined_table_data.append({
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'phone': user.phone, 
                    'first_name': user.first_name, 
                    'last_name': user.last_name, 
                    'other_name': user.other_name, 
                    'logo': user.logo, 
                    'account_type': user.account_type, 
                    'created_by': user.created_by,
                    'updated_by': user.updated_by,
                    'created_on': user.created_on.strftime("%Y-%m-%d %H:%M:%S"),
                    'updated_on': user.updated_on.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        # Convert the result to a JSON-formatted string
        result_json = json.dumps(joined_table_data, indent=2)
        return  result_json

    def createUser(_first_name, _last_name, _other_name, _business_name, _password, _email, _phone, _description, _role, _digital_address, _address, business_detail):
        user_id = str(uuid.uuid4())
        new_user = User( email=_email, password=_password, role=_role, phone=_phone, first_name=_first_name, last_name=_last_name, other_name=_other_name, created_by=_email, updated_by=_email, business_id=business_detail.business_id, id=user_id )
        try:
            # Start a new session
            with app.app_context():
                db.session.add(new_user)
        except Exception as e:
            # db.session.rollback()  # Rollback the transaction in case of an error
            print(f"Error:: {e}")
        finally:
            # db.session.close()
            db.session.commit()
            db.session.close()
        return new_user

    def update_user(_key, _value, _user_data):
        if _key == 'password':
            password = hashlib.sha256((_value).encode()).hexdigest()
            # print(_key, _value, _user_data)
            _user_data.password = password
            # print(password)
        db.session.commit()

    def delete_user(_id):
        is_successful = User.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)

class School(db.Model):
    __tablename__ = 'school'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    programme = db.relationship('Programme', back_populates='school')
    # Add a foreign key, reference to the User table
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    # Define a relationship to access the User object from a User object
    user = db.relationship('User', back_populates='school')
    file = db.relationship('Fileupload', back_populates='school')


    def create_school(user_id: str, name: str = None, description: str = None, **kwargs):
        _id = str(uuid.uuid4())
        try:
            school = School(id=_id, user_id=user_id, name=name, description=description, **kwargs)
            db.session.add(school)
            db.session.commit()
            logger.info(f"School created with ID: {school.id}")
            return school
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating school: {e}")
            raise

    def get_school_by_id(school_id: str):
        try:
            school = db.session.query(School).filter(School.id == school_id).one_or_none()
            if school:
                logger.info(f"School retrieved with ID: {school_id}")
            else:
                logger.warning(f"No school found with ID: {school_id}")
            return school
        except Exception as e:
            logger.error(f"Error retrieving school by ID: {e}")
            raise

    def get_all_schools():
        try:
            schools = db.session.query(School).all()
            logger.info(f"Retrieved {len(schools)} schools")
            return schools
        except Exception as e:
            logger.error(f"Error retrieving all schools: {e}")
            raise

    def update_school(school_id: str, **kwargs):
        try:
            school = db.session.query(School).filter(School.id == school_id).one_or_none()
            if school:
                for key, value in kwargs.items():
                    setattr(school, key, value)
                school.updated_on = datetime.utcnow()
                db.session.commit()
                logger.info(f"School updated with ID: {school.id}")
            else:
                logger.warning(f"No school found with ID: {school_id}")
            return school
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating school: {e}")
            raise

    def delete_school(school_id: str):
        try:
            school = db.session.query(School).filter(School.id == school_id).one_or_none()
            if school:
                db.session.delete(school)
                db.session.commit()
                logger.info(f"School deleted with ID: {school_id}")
                return True
            else:
                logger.warning(f"No school found with ID: {school_id}")
                return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting school: {e}")
            raise

class Student(db.Model):
    __tablename__ = 'student'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()), unique=True, nullable=False)
    description = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the User table
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    application_id = db.Column(db.String(36), db.ForeignKey('application.id'))
    # Define a relationship to access the User object from a User object
    user = db.relationship('User', back_populates='student')
    application = db.relationship('Application', back_populates='student')

    def create_student(user_id: str, application_id: str, description: str = None, **kwargs):
        _id = str(uuid.uuid4())
        try:
            student = Student(id=_id, user_id=user_id, application_id=application_id, description=description, **kwargs)
            db.session.add(student)
            db.session.commit()
            logger.info(f"Student created with ID: {student.id}")
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating student: {e}")
            raise

    def get_student_by_id(student_id: str):
        try:
            student = db.session.query(Student).filter(Student.id == student_id).one_or_none()
            if student:
                logger.info(f"Student retrieved with ID: {student_id}")
            else:
                logger.warning(f"No student found with ID: {student_id}")
            return student
        except Exception as e:
            logger.error(f"Error retrieving student by ID: {e}")
            raise

    def get_all_students():
        try:
            students = db.session.query(Student).all()
            logger.info(f"Retrieved {len(students)} students")
            return students
        except Exception as e:
            logger.error(f"Error retrieving all students: {e}")
            raise

    def update_student(student_id: str, **kwargs):
        try:
            student = db.session.query(Student).filter(Student.id == student_id).one_or_none()
            if student:
                for key, value in kwargs.items():
                    setattr(student, key, value)
                student.updated_on = datetime.utcnow()
                db.session.commit()
                logger.info(f"Student updated with ID: {student.id}")
            else:
                logger.warning(f"No student found with ID: {student_id}")
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating student: {e}")
            raise

    def delete_student(student_id: str):
        try:
            student = db.session.query(Student).filter(Student.id == student_id).one_or_none()
            if student:
                db.session.delete(student)
                db.session.commit()
                logger.info(f"Student deleted with ID: {student_id}")
                return True
            else:
                logger.warning(f"No student found with ID: {student_id}")
                return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting student: {e}")
            raise


class Application(db.Model):
    __tablename__ = 'application'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()), unique=True, nullable=False)
    description = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    student = db.relationship('Student', back_populates='application')
    programme = db.relationship('Programme', back_populates='application')

    def create_application(description: str = None, **kwargs):
        _id = str(uuid.uuid4())
        try:
            application = Application(id=_id, description=description, **kwargs)
            db.session.add(application)
            db.session.commit()
            logger.info(f"Application created with ID: {application.id}")
            return application
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating application: {e}")
            raise

    def get_application_by_id(application_id: str):
        try:
            application = db.session.query(Application).filter(Application.id == application_id).one_or_none()
            if application:
                logger.info(f"Application retrieved with ID: {application_id}")
            else:
                logger.warning(f"No application found with ID: {application_id}")
            return application
        except Exception as e:
            logger.error(f"Error retrieving application by ID: {e}")
            raise

    def get_all_applications():
        try:
            applications = db.session.query(Application).all()
            logger.info(f"Retrieved {len(applications)} applications")
            return applications
        except Exception as e:
            logger.error(f"Error retrieving all applications: {e}")
            raise

    def update_application(application_id: str, **kwargs):
        try:
            application = db.session.query(Application).filter(Application.id == application_id).one_or_none()
            if application:
                for key, value in kwargs.items():
                    setattr(application, key, value)
                application.updated_on = datetime.utcnow()
                db.session.commit()
                logger.info(f"Application updated with ID: {application.id}")
            else:
                logger.warning(f"No application found with ID: {application_id}")
            return application
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating application: {e}")
            raise

    def delete_application(application_id: str):
        try:
            application = db.session.query(Application).filter(Application.id == application_id).one_or_none()
            if application:
                db.session.delete(application)
                db.session.commit()
                logger.info(f"Application deleted with ID: {application_id}")
                return True
            else:
                logger.warning(f"No application found with ID: {application_id}")
                return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting application: {e}")
            raise

class Programme(db.Model):
    __tablename__ = 'programme'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the school table
    school_id = db.Column(db.String(36), db.ForeignKey('school.id'))
    # Add a foreign key, reference to the application table
    application_id = db.Column(db.String(36), db.ForeignKey('application.id'))
    # Define a relationship to access the school object from a User object
    school = db.relationship('School', back_populates='programme')
    # Define a relationship to access the application object from a User object
    application = db.relationship('Application', back_populates='programme')

    def create_programme(school_id: str, application_id: str, name: str = None, description: str = None, **kwargs):
        _id = str(uuid.uuid4())
        try:
            programme = Programme(school_id=school_id, application_id=application_id, name=name, description=description, **kwargs)
            db.session.add(programme)
            db.session.commit()
            logger.info(f"Programme created with ID: {programme.id}")
            return programme
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating programme: {e}")
            raise

    def get_programme_by_id(programme_id: str):
        try:
            programme = db.session.query(Programme).filter(Programme.id == programme_id).one_or_none()
            if programme:
                logger.info(f"Programme retrieved with ID: {programme_id}")
            else:
                logger.warning(f"No programme found with ID: {programme_id}")
            return programme
        except Exception as e:
            logger.error(f"Error retrieving programme by ID: {e}")
            raise

    def get_all_programmes():
        try:
            programmes = db.session.query(Programme).all()
            logger.info(f"Retrieved {len(programmes)} programmes")
            return programmes
        except Exception as e:
            logger.error(f"Error retrieving all programmes: {e}")
            raise

    def update_programme(programme_id: str, **kwargs):
        try:
            programme = db.session.query(Programme).filter(Programme.id == programme_id).one_or_none()
            if programme:
                for key, value in kwargs.items():
                    setattr(programme, key, value)
                programme.updated_on = datetime.utcnow()
                db.session.commit()
                logger.info(f"Programme updated with ID: {programme.id}")
            else:
                logger.warning(f"No programme found with ID: {programme_id}")
            return programme
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating programme: {e}")
            raise

    def delete_programme(programme_id: str):
        try:
            programme = db.session.query(Programme).filter(Programme.id == programme_id).one_or_none()
            if programme:
                db.session.delete(programme)
                db.session.commit()
                logger.info(f"Programme deleted with ID: {programme_id}")
                return True
            else:
                logger.warning(f"No programme found with ID: {programme_id}")
                return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting programme: {e}")
            raise

class Code(db.Model):
    __tablename__ = 'code'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()), unique=True, nullable=False)
    code = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(80), nullable=True)
    account = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def createCode(_email, _code, _type):
        # cron job to delete expired used user sessions
        Code.objects.filter(update_at__lte=(timezone.now()-timedelta(seconds=5)) ).delete()
        _id = str(uuid.uuid4())
        new_data = Code( account=_email, code=_code, type=_type, id=_id )
        try:
            # Start a new session
            with app.app_context():
                db.session.add(new_data)
        except Exception as e:
            # db.session.rollback()  # Rollback the transaction in case of an error
            print(f"Error:: {e}")
        finally:
            db.session.commit()
            db.session.close()
            pass
        return new_data
    
    def delete_code(_id):
        is_successful = Code.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)

    # get transacttion by ID
    def getCodeById(id, page=1, per_page=10):        
        # Determine the page and number of items per page from the request (if provided)
        # Query the database with pagination
        pagination = Code.query.filter_by(id=id).paginate(page=page, per_page=per_page, error_out=False)

        # Extract the items for the current page
        new_data = pagination.items
        # Render nested objects
        new_data_object = [alchemy_to_json(item) for item in new_data]
        # Prepare pagination information to be returned along with the data
        pagination_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }
        return {
            'data': new_data_object,
            'pagination': pagination_data
        }

class Fileupload(db.Model):
    __tablename__ = 'file'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()), unique=True, nullable=False)
    file = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the user table
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))    
    user = db.relationship('User', back_populates='file')
    # Add a foreign key, reference to the school table
    school_id = db.Column(db.String(36), db.ForeignKey('school.id'))
    school = db.relationship('School', back_populates='file')
    
    # get file by business
    def getFileById(id, page=1, per_page=10): 
        pagination = Fileupload.query.filter_by(id=id).paginate(page=page, per_page=per_page, error_out=False)
        # Extract the items for the current page
        new_data = pagination.items
        # Render nested objects
        new_data_object = [alchemy_to_json(item) for item in new_data]
        # Prepare pagination information to be returned along with the data
        pagination_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }
        return {
            'data': new_data_object,
            'pagination': pagination_data
        }

    def createFile(_file, _description, _user_id, _school_id):
        _id = str(uuid.uuid4())
        # print(_id, _file)
        new_data = Fileupload( file=_file, description=_description, id=_id )
        try:
            # Start a new session
            with app.app_context():
                db.session.add(new_data)
                db.session.commit()
                # Refresh the instance to make sure attributes are up-to-date
                db.session.refresh(new_data)
        except Exception as e:
            db.session.rollback()  # Rollback the transaction in case of an error
            # return str(e)
        finally:
            db.session.close()
        return new_data

    def updateFile(file, description, business, id):
        # print(">>>>>>>>", id, db.session.query(Fileupload).filter(id==id).first())
        new_data = Fileupload.query.filter_by(id=id).first()
        if file:
            new_data.file = file
        if description:
            new_data.description = description
        db.session.commit()
        print(">>>", new_data.updated_on)
        # db.session.close()
        return alchemy_to_json(new_data)

    def delete_file(_id):
        is_successful = Fileupload.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)
