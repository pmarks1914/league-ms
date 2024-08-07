
from asyncio.log import logger
import email
from enum import unique
import hashlib
from locale import currency
import re
from textwrap import indent
from time import timezone
from flask import request
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import defer, undefer, relationship, load_only, sessionmaker
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy import ForeignKey
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.inspection import inspect
from sqlalchemy.sql.expression import func
from Helper.helper import generate_transaction_referance
from Settings import app
from datetime import datetime, timedelta
# from flask_script import Manager
from flask_migrate import Migrate
import json
# from sendEmail import Email 
import uuid
import sys
from dotenv import dotenv_values

get_env = dotenv_values(".env") 
db = SQLAlchemy(app)
migrate = Migrate(app, db)
 
list_account_status = ['PENDING', 'APPROVED', 'REJECTED']
list_status = ['PENDING', 'SUCCESSFULL', 'FAILED']
list_other_info = ["user_preference_email", "user_preference_phone", "purpose_evaluation", "institution_name", "department_office", "contact_person", "contact_person_email", "payment_method", "billing_address", "verification_status", "reference_email", "reference_phone"]

def alchemy_to_json(obj, visited=None):
    if visited is None:
        visited = set()
    if id(obj) in visited:
        return None  # Prevent infinite recursion
    visited.add(id(obj))
    
    if isinstance(obj.__class__, DeclarativeMeta):
        fields = {}
        # Determine the role and exclude fields accordingly
        if hasattr(obj, 'role') and obj.role == 'STUDENT':
            exclude_fields = ["query", "registry", "query_class", "password", "student"]
        else:
            exclude_fields = ["query", "registry", "query_class", "password"]

        for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata' and x not in exclude_fields]:
            data = getattr(obj, field)
            try:
                if not callable(data):
                    # Handle SQLAlchemy relationships
                    if isinstance(data.__class__, DeclarativeMeta):
                        fields[field] = alchemy_to_json(data, visited)
                    elif isinstance(data, list) and data and isinstance(data[0].__class__, DeclarativeMeta):
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
    else:
        return obj

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    other_name = db.Column(db.String(80), nullable=True)
    active_status = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    address = db.Column(db.String(50), nullable=True)
    country = db.Column(db.String(50), nullable=True)
    city = db.Column(db.String(50), nullable=True)
    town = db.Column(db.String(50), nullable=True)
    lon = db.Column(db.String(25), nullable=True)
    lat = db.Column(db.String(25), nullable=True)
    dob = db.Column(db.DateTime(), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    other_info = db.Column(JSON, nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    school = db.relationship('School',  back_populates='user', lazy='joined')
    student = db.relationship('Student', back_populates='user', lazy='select')
    file = db.relationship('Fileupload', back_populates='user', lazy='select')
    
    def json(self):
        return {
                'id': self.id,
                'email': self.email,
                'role': self.role,
                'first_name': self.first_name, 
                'last_name': self.last_name, 
                'other_name': self.other_name, 
                'phone': self.phone, 
                'lat': self.lat, 
                'lon': self.lon, 
                'town': self.town, 
                'city': self.city,
                'country': self.country,
                'address': self.address, 
                'other_info': self.other_info,
                # 'logo': self.logo, 
                'created_by': self.created_by,
                'updated_by': self.updated_by,
                'created_on': str(self.created_on),
                'updated_on': str(self.updated_on),
                'file': [file.to_dict() for file in self.file]
                }
    def _repr_(self):
        return json.dumps({
                'id': self.id,
                'email': self.email,
                'role': self.role,
                'first_name': self.first_name, 
                'last_name': self.last_name, 
                'other_name': self.other_name, 
                'country': self.country, 
                'other_info': self.other_info,
                'created_by': self.created_by,
                'updated_by': self.updated_by,
                'created_on': self.created_on,
                'updated_on': self.updated_on })
    def username_password_match(_username, _password ):
        new_data = User.query.filter_by(email=_username, password=_password).first()
        if new_data is None:
            return False
        elif new_data.role == 'STUDENT':
            new_data_object = alchemy_to_json(new_data)
            return new_data_object

    def getAllUsers(page, per_page):        
        # Determine the page and number of items per page from the request (if provided)
        # Query the database with pagination
        pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
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

    def getUserById(id):
        new_data = User.query.filter_by(id=id).first()
        new_data_object = new_data.json()
        return new_data_object

    def getUserByEmail(email):
        new_data = User.query.filter_by(email=email).first()
        new_data_object = alchemy_to_json(new_data)
        return new_data_object

    def getAllUsersByEmail(_email):
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
                    'first_name': user.first_name, 
                    'last_name': user.last_name, 
                    'other_name': user.other_name, 
                    'country': user.country, 
                    'created_by': user.created_by,
                    'updated_by': user.updated_by,
                    'created_on': user.created_on.strftime("%Y-%m-%d %H:%M:%S"),
                    'updated_on': user.updated_on.strftime("%Y-%m-%d %H:%M:%S")
                }
            })
        # Convert the result to a JSON-formatted string
        result_json = json.dumps(joined_table_data, indent=2)
        return  result_json

    def createUser(_first_name, _last_name, _other_name, _password, _email, _description, _role, _address, **kwargs):
        user_id = str(uuid.uuid4())
        new_user = User( email=_email, password=_password, role=_role, first_name=_first_name, last_name=_last_name, other_name=_other_name, created_by=_email, updated_by=_email, id=user_id )
        try:
            # Start a new session
            with app.app_context():
                db.session.add(new_user)
                db.session.commit()
                Student.create_student(user_id, None, _email)
        except Exception as e:
            db.session.rollback()  # Rollback the transaction in case of an error
            print(f"Error:: {e}")
        finally:
            # db.session.close()
            pass
        return new_user

    def update_user( _id, _value, _user_data):
        _user_data = User.query.filter_by(id=_id).first()
        _user_data.password = hashlib.sha256((_value).encode()).hexdigest()
        db.session.commit()
        return True

    def update_email_user( _email, _value, _user_data):
        _user_data = User.query.filter_by(email=_email).first()
        _user_data.password = hashlib.sha256((_value).encode()).hexdigest()
        db.session.commit()
        return True

    def update_user_any(user_id, updated_by, **kwargs):
        try:
            user = db.session.query(User).filter(User.id == user_id).one_or_none() or []
            if user:
                for key, value in kwargs.items():
                    # allow for other info
                    if key in list_other_info:
                        if user.other_info:
                            user.other_info = user.other_info | {key: value}
                        else:
                            user.other_info = {key: value}
                    else:
                        setattr(user, key, value)
                user.updated_on = datetime.utcnow()
                user.updated_by = updated_by
                db.session.commit()
                logger.info(f"user updated with ID: {user.id}")
            else:
                logger.warning(f"No user found with ID: {user_id}")
            return user.json()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user: {e}")
            raise
    
    def delete_user(_id):
        is_successful = User.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)

class School(db.Model):
    __tablename__ = 'school'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(80), nullable=True)
    expected_applicantion = db.Column(db.Integer, nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the User table
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'), nullable=False)
    # Define a relationship to access the User object from a User object
    user = db.relationship('User',  back_populates='school', lazy='joined')
    file = db.relationship('Fileupload', back_populates='school', lazy='select')
    programme = db.relationship('Programme', back_populates='school')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'expected_applicantion': self.expected_applicantion,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on),
            # "user": self.user.json() if self.user else None,
        }
    
    def to_dict_2(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'expected_applicantion': self.expected_applicantion,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on),
            # "user": self.user.json() if self.user else None,
            'programme': [programme.to_dict_2() for programme in self.programme]

        }

    def countSchool():
        return School.query.count()

    def create_school(user_id, name, description, expected_applicantion, user_email):
        _id = str(uuid.uuid4())
        sys.setrecursionlimit(30000)
        try:
            school = School(id=_id, user_id=user_id, name=name, description=description, expected_applicantion=expected_applicantion, updated_by=user_email, created_by=user_email) 
            db.session.add(school)
            db.session.commit()
            logger.info(f"School created with ID: {school.id}")
            return school
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating school: {e}")
            raise

    def get_school_by_two():
        joined_table_data = []
        school = School.query.order_by(func.random()).all() 
        # school = School.query.order_by(func.random()).limit(2).all() 
        # Render nested objects
        if school:
            logger.info(f"Schools retrieved")
            for item in school:
                joined_table_data.append(item.to_dict_2())
            # Convert the result to a JSON-formatted string
        else:
            logger.warning(f"No schools found")
        return joined_table_data

    def get_school_by_id(school_id):
        try:
            school = db.session.query(School).filter(School.id == school_id).one_or_none() or []
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

    def update_school(school_id, updated_by, **kwargs):
        try:
            school = db.session.query(School).filter(School.id == school_id).one_or_none() or []
            if school:
                for key, value in kwargs.items():
                    setattr(school, key, value)
                school.updated_on = datetime.utcnow()
                school.updated_by = updated_by
                db.session.commit()
                logger.info(f"School updated with ID: {school.id}")
            else:
                logger.warning(f"No school found with ID: {school_id}")
            return school
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating school: {e}")
            raise

    def delete_school(school_id):
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    description = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the User table
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))
    # Define a relationship to access the User object from a User object
    user = db.relationship('User', back_populates='student', lazy='select')
    application = db.relationship('Application', back_populates='student', lazy='select')

    # def _repr_(self):
    #     return {
    #             'id': self.id,
    #             'description': self.description,
    #             'user_id': self.user_id,
    #             'created_by': self.created_by,
    #             'updated_by': self.updated_by,
    #             'created_on': self.created_on,
    #             'updated_on': self.updated_on }
        
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'description': self.description,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on),
            "user": self.user.json() if self.user else None,
        }

    def create_student(user_id, description, user_email):
        _id = str(uuid.uuid4())
        try:
            student = Student(id=_id, user_id=user_id, description=description, updated_by=user_email, created_by=user_email) 
            db.session.add(student)
            db.session.commit()
            logger.info(f"Student created with ID: {student.id}")
            return student
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating student: {e}")
            raise

    def get_student_by_id(student_id):
        try:
            student = db.session.query(Student).filter(Student.id == student_id).one_or_none() or []
            if student:
                logger.info(f"Student retrieved with ID: {student_id}")
            else:
                logger.warning(f"No student found with ID: {student_id}")
            return student
        except Exception as e:
            logger.error(f"Error retrieving student by ID: {e}")
            raise
    
    def get_user_by_id(id):
        try:
            student = db.session.query(Student).filter(Student.user_id == id).first() or []
            if student:
                logger.info(f"Student retrieved with ID: {id}")
            else:
                logger.warning(f"No student found with ID: {id}")
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

    def update_student(student_id, updated_by, **kwargs):
        try:
            student = db.session.query(Student).filter(Student.id == student_id).one_or_none() or []
            if student:
                for key, value in kwargs.items():
                    setattr(student, key, value)
                student.updated_on = datetime.utcnow()
                student.updated_by = updated_by
                db.session.commit()
                logger.info(f"Student updated with ID: {student.id}")
            else:
                logger.warning(f"No student found with ID: {student_id}")
            return student.to_dict()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating student: {e}")
            raise

    def delete_student(student_id):
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    description = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    progress = db.Column(db.Integer, nullable=True)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    student_id = db.Column(db.String(36), db.ForeignKey('student.id'))
    programme = db.relationship('Programme', back_populates='application', lazy='select')
    student = db.relationship('Student', back_populates='application', lazy='select')
    programme_id = db.Column(db.String(36), db.ForeignKey('programme.id'))

    def application_json(self):
        return {
            'id': self.id,
            'description': self.description,
            'student_id': self.student_id,
            'programme_id': self.programme_id,
            'progress': self.progress,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on),
            'student': self.student.to_dict() if self.student else None,
            'programme': self.programme.to_dict() if self.programme else None }

    def countApplicationById(student_id):
        return Application.query.filter_by(student_id=student_id).count()

    def create_application(description, programme_id, student_id, user_email):
        _id = str(uuid.uuid4())
        try:
            application = Application(id=_id, description=description, programme_id=programme_id, student_id=student_id, updated_by=user_email, created_by=user_email, progress=25)
            db.session.add(application)
            db.session.commit()
            logger.info(f"Application created with ID: {application.id}")
            return application
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating application: {e}")
            raise

    def get_application_by_id(application_id):
        try:
            application = db.session.query(Application).filter(Application.id == application_id).one_or_none() or []
            if application:
                logger.info(f"Application retrieved with ID: {application_id}")
            else:
                logger.warning(f"No application found with ID: {application_id}")
            return application
        except Exception as e:
            logger.error(f"Error retrieving application by ID: {e}")
            raise
    
    # get application by student id for last five
    def get_application_by_student_id_last_five(student_id, page, per_page): 
        pagination = Application.query.filter_by(student_id=student_id).order_by(Application.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
        # Extract the items list for the current page
        new_data = pagination.items
        # Render nested objects
        pagination_data = [Application.application_json(appli) for appli in new_data]
        # Prepare pagination information to be returned along with the data
        paging_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }
        return {
            'data': pagination_data,
            'pagination': paging_data
        }

    # get application by student id
    def get_application_by_student_id(student_id, page, per_page): 
        pagination = Application.query.filter_by(student_id=student_id).paginate(page=page, per_page=per_page, error_out=False)
        # Extract the items list for the current page
        new_data = pagination.items
        # Render nested objects
        pagination_data = [Application.application_json(appli) for appli in new_data]
        # Prepare pagination information to be returned along with the data
        paging_data = {
            'total': pagination.total,
            'per_page': per_page,
            'current_page': page,
            'total_pages': pagination.pages
        }
        return {
            'data': pagination_data,
            'pagination': paging_data
        }

    def get_all_applications():
        try:
            applications = db.session.query(Application).all()
            logger.info(f"Retrieved {len(applications)} applications")
            return applications
        except Exception as e:
            logger.error(f"Error retrieving all applications: {e}")
            raise

    def update_application(application_id, updated_by, **kwargs):
        try:
            application = db.session.query(Application).filter(Application.id == application_id).one_or_none() or []
            if application:
                for key, value in kwargs.items():
                    setattr(application, key, value)
                application.updated_on = datetime.utcnow()
                application.updated_by = updated_by
                db.session.commit()
                logger.info(f"Application updated with ID: {application.id}")
            else:
                logger.warning(f"No application found with ID: {application_id}")
            return application
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating application: {e}")
            raise

    def delete_application(application_id):
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the school table
    school_id = db.Column(db.String(36), db.ForeignKey('school.id'))
    # Add a foreign key, reference to the application table
    # application_id = db.Column(db.String(36), db.ForeignKey('application.id'))
    # Define a relationship to access object
    school = db.relationship('School', back_populates='programme', lazy='select')
    school = db.relationship('School', back_populates='programme', lazy='select')
    application = db.relationship('Application', back_populates='programme', lazy='select')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on),
            "school": self.school.to_dict() if self.school else None,
        }
    def to_dict_2(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on),
        }

    def countProgramme():
        return Programme.query.count()

    def create_programme(school_id, name, description, user_email):
        _id = str(uuid.uuid4())
        try:
            programme = Programme(id=_id, school_id=school_id, name=name, description=description, updated_by=user_email, created_by=user_email)
            db.session.add(programme)
            db.session.commit()
            logger.info(f"Programme created with ID: {programme.id}")
            return programme
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating programme: {e}")
            raise

    def get_programme_by_id(programme_id):
        try:
            programme = db.session.query(Programme).filter(Programme.id == programme_id).one_or_none() or []
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

    def update_programme(programme_id, updated_by, **kwargs):
        try:
            programme = db.session.query(Programme).filter(Programme.id == programme_id).one_or_none() or []
            if programme:
                for key, value in kwargs.items():
                    if key in ['name', 'description', 'school_id']:
                        setattr(programme, key, value)
                programme.updated_on = datetime.utcnow()
                programme.updated_by = updated_by
                db.session.commit()
                logger.info(f"Programme updated with ID: {programme.id}")
            else:
                logger.warning(f"No programme found with ID: {programme_id}")
            return programme
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating programme: {e}")
            raise

    def delete_programme(programme_id):
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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    code = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(80), nullable=True)
    account = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def createCode(_email, _code, _type):
        # cron job to delete expired used user sessions
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        Code.query.filter(Code.updated_on <= cutoff_time).delete()
        db.session.commit()

        _id = str(uuid.uuid4())
        new_data = Code( account=_email, code=_code, type=_type, id=_id )
        try:
            # Start a new session
            with app.app_context():
                db.session.add(new_data)
                db.session.commit()
        except Exception as e:
            # db.session.rollback()  # Rollback the transaction in case of an error
            print(f"Error:: {e}")
        finally:
            # db.session.commit()
            # db.session.close()
            pass
        return new_data
    
    def delete_email_code(_code, _email):
        is_successful = Code.query.filter_by(account=_email, code=_code).delete()
        db.session.commit()
        return bool(is_successful)
    
    def delete_code(_id):
        is_successful = Code.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)

    def getCodeByOTP(_otp, email):
        if Code.query.filter_by(code=_otp).filter_by(account=email).first():
            return Code.query.filter_by(code=_otp).filter_by(account=email).first()
        else:
            return None

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
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()), unique=True, nullable=False)
    file = db.Column(db.String(80), nullable=True)
    type = db.Column(db.String(80), nullable=True)
    format = db.Column(db.String(80), nullable=True)
    issued_date = db.Column(db.DateTime(), nullable=True)
    slug = db.Column(db.String(80), nullable=True)
    description = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the user table
    user_id = db.Column(db.String(36), db.ForeignKey('user.id'))    
    user = db.relationship('User', back_populates='file', lazy='select')
    # Add a foreign key, reference to the school table
    school_id = db.Column(db.String(36), db.ForeignKey('school.id'))
    school = db.relationship('School', back_populates='file', lazy='select')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.file,
            'type': self.type,
            'format': self.format,
            'url': get_env['FILE_STATIC_UPLOAD_PATH_READ'] + str(self.id) + '.' + self.format,
            'description': self.description,
            'created_on': str(self.created_on),
            'updated_on': str(self.updated_on)
        }

    def countFileById(user_id):
        return Fileupload.query.filter_by(user_id=user_id).count()

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

    def createFile(_file, _description, _file_type, _doc_format, _user_id, _issued_date, _slug):
        _id = str(uuid.uuid4())
        new_data = Fileupload( file=_file, description=_description, id=_id, type=_file_type, format=_doc_format, user_id=_user_id, issued_date=_issued_date, slug=_slug)

        try:
            # Start a new session
            db.session.add(new_data)
            db.session.commit()
            return new_data
        except Exception as e:
            db.session.rollback()  # Rollback the transaction in case of an error
            print(f"Error:: {e}")
        finally:
            # db.session.close()
            pass
 
    def updateFile(file, description, business, id):
        new_data = Fileupload.query.filter_by(id=id).first()
        if file:
            new_data.file = file
        if description:
            new_data.description = description
        db.session.commit()
        # db.session.close()
        return alchemy_to_json(new_data)

    def delete_file(_id):
        is_successful = Fileupload.query.filter_by(id=_id).delete()
        db.session.commit()
        return bool(is_successful)
