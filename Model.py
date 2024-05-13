
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
    phone = db.Column(db.String(15), nullable=True) # datatype
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    other_name = db.Column(db.String(80), nullable=True)
    logo = db.Column(db.String(120), nullable=True)
    account_type = db.Column(db.String(22), nullable=True) 
    active_status = db.Column(db.String(80), nullable=True)
    created_by = db.Column(db.String(80), nullable=True)
    updated_by = db.Column(db.String(80), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add a foreign key, reference to the Business table
    business_id = db.Column(db.String(36), db.ForeignKey('business.business_id'))
    # Define a relationship to access the Business object from a User object
    business = db.relationship('Business', back_populates='user')
    
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
        user_data = db.session.query(User, Business).filter_by(email=_email).join(Business).all()

        # get joined tables data
        for user, business in user_data:
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
                    'business_id': user.business_id, 
                    'created_on': user.created_on.strftime("%Y-%m-%d %H:%M:%S"),
                    'updated_on': user.updated_on.strftime("%Y-%m-%d %H:%M:%S")
                },
                'business': {
                    'business_name': business.business_name,
                    'business_id': business.business_id,
                    'business_name': business.business_name,
                    'email': business.email,
                    'phone': business.phone,
                    'digital_address': business.digital_address,
                    'address': business.address,
                    'business_account_status': business.business_account_status,
                    'created_by': business.created_by,
                    'updated_by': business.updated_by,
                    'created_on': business.created_on.strftime("%Y-%m-%d %H:%M:%S"),
                    'updated_on': business.updated_on.strftime("%Y-%m-%d %H:%M:%S"),
                    'kyc_id': business.kyc_id,
                    'settlement_id': business.settlement_id,
                    'apikey_id': business.apikey_id
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
    description = db.Column(db.String(80), nullable=True)
    business = db.relationship('Business', back_populates='file')
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_on = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)

    def getFileById(id):
        new_data = db.session.query(Fileupload).filter(id==id).first()
        # print(new_data)
        if new_data:
            return alchemy_to_json(new_data)
    
    # get file by business
    def getFileByBusinesId(id, page=1, per_page=10): 
        pagination = Apikey.query.filter_by(apikey_id=id).paginate(page=page, per_page=per_page, error_out=False)
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

    def createFile(_file, _description, _business):
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