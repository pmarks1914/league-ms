from crypt import methods
import re
import uuid
from flask import Flask, jsonify, request, Response, render_template
import requests, json
from Helper.helper import generate_random_code
from fileManager.fileManager import fileUpload
#import geocoder
from Model import Application, Programme, School, Student, User, Code, db, Fileupload
from Notification.Email.sendEmail import send_notification_email
# from sendEmail import Email 
from Settings import *
import jwt, datetime
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from functools import wraps
from flask_cors import CORS
import hashlib
# from pyisemail import is_email 
import sys
#import winrt.windows.devices.geolocation as wdg, asyncio
from email.mime.text import MIMEText
#from safrs import SAFRSBase, SAFRSAPI
#from api_spec import spec
#from swagger import swagger_ui_blueprint, SWAGGER_URL
# Created instance of the class
from dotenv import dotenv_values


get_env = dotenv_values(".env")  

CORS(app)
# CORS(app, resources={r"/*": {"origins": "*"}})
app.config['SECRET_KEY'] = get_env['SECRET_KEY']        
 

    
def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        token = token.split(" ")[1]        
        if not token:
            return jsonify({'error': 'Token is missing', 'code': 401}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            return f(*args, **kwargs)
        except ExpiredSignatureError :
            return jsonify({'error': 'Token has expired', 'code': 401}), 401
        except InvalidTokenError:
            return jsonify({'error': 'Invalid Token', 'code': 401}), 401
        except Exception as e:
            return jsonify({'error': str(e), 'code': 401}), 401
    return wrapper

@app.route('/test', methods=['GET'])
# @token_required
def testd():
    try:
        # Extract query parameters
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)
        user = User.getAllUsers(page, per_page)

        msg = {
            "code": 200,
            "message": 'Successful',
            "user": user['data'],
            "pagination": user['pagination']
        }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response    
    except Exception as e:
        return {"tes": str(e)}

@app.route('/v1/callback/mfs', methods=['POST'])
def callbackfs():
    try:
        request_data = request.json
        # print("mfs callback >>> ", request_data )
        msg = {
            "code": 200,
            "message": 'Successful',
            "data": request_data
        }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response 
    except Exception as e:
        return {"tes": str(e)}

@app.route('/login', methods=['POST'])
def get_token():
    student_id = None
    request_data = request.get_json()
    password_hashed = hashlib.sha256((request_data.get('password')).encode()).hexdigest()
    try:
        match = User.username_password_match(request_data.get('email'), password_hashed)
        if match != None and match != False:
            expiration_date = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
            token = jwt.encode({'exp': expiration_date, 'id': match['id']}, app.config['SECRET_KEY'], algorithm='HS256')
            if match['role'] == 'STUDENT':
                student_id = Student.get_user_by_id(match['id']) or None
                student_id = student_id.id or None
            msg = { "user": match | {"student_id":  student_id}, "access_key": jwt.decode( token, app.config['SECRET_KEY'], algorithms=['HS256'] ), "token": token }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        else:
            invalidUserOjectErrorMsg= {"code": 404, "User unavailable": 'Failed'}
            return Response(json.dumps(invalidUserOjectErrorMsg), status=404, mimetype='application/json')
    except Exception as e:
            invalidUserOjectErrorMsg= {"code": 500, "message": 'Failed', "error": str(e)}
            return Response(json.dumps(invalidUserOjectErrorMsg), status=500, mimetype='application/json')

@app.route('/user/<string:id>', methods=['GET'])
@token_required
def user(id):
    if request.method == 'GET':
        try:
            request_data = User.getUserById(id)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
        
@app.route('/v1/registration', methods=['POST'])
def add_user_registration():
    request_data = request.get_json()
    msg = {}
    code = request_data.get('otp')
    email = request_data.get('email')
    if request_data.get('password1') == None or request_data.get('email') == None:
        msg = {
            "code": 305,
            "message": 'Password or Email is required'
        }
        response = Response(json.dumps(msg), status=200, mimetype='application/json')
        return response 
    elif Code.getCodeByOTP(code, email) is None:
        return jsonify({ 'code': 403, 'message': 'Resource not found, check your email for the required code'}), 403

    try:
        _password = hashlib.sha256((request_data.get('password1')).encode()).hexdigest()
        _first_name = request_data.get('first_name')
        _last_name = request_data.get('last_name')
        _other_name = request_data.get('other_name')
        _email = request_data.get('email')
        # _phone = request_data.get('phone')
        _description = request_data.get('description')
        _role = request_data.get('role')
        _address = request_data.get('address')

        if User.query.filter_by(email=request_data.get('email')).first() is not None:
            msg = {
                "code": 202,
                "error": "user already registtered"
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response
        else:
            User.createUser(_first_name, _last_name, _other_name, _password, _email, _description, _role, _address)
            invalidUserOjectErrorMsg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    "first_name": request_data.get('first_name'),
                    "last_name": request_data.get('last_name'),
                    "other_name": request_data.get('other_name'),
                    "email": request_data.get('email'),
                    "description": request_data.get('description'),
                    "role": request_data.get('role'),
                    "address": request_data.get('address')
                }
            }
            response = Response(json.dumps(invalidUserOjectErrorMsg), status=200, mimetype='application/json')
            return response
    except Exception as e:
        invalidUserOjectErrorMsg = {
            "code": 204,
            "error": str(e)
        }
        response = Response(json.dumps(invalidUserOjectErrorMsg), status=200, mimetype='application/json')
        return response
  
@app.route('/v1/change/password/<string:id>', methods=['PATCH'])
def update_password(id):
    # Fetch the resource from your data source (e.g., database)
    request_data = request.get_json()
    resource = User.getUserById(id)
    validate_list = ["id", "password1", "password2", "code", "email"]
    validate_status = False
    msg = {}
    if resource is None:
        return jsonify({ 'code': 404, 'error': 'Resource not found'}), 404
    elif Code.getCodeByOTP(request_data.get('code'), request_data.get('email') ) is None:
        return jsonify({ 'code': 403, 'error': 'Resource not found, check your email for the required code'}), 404
    # Get the data from the request
    data = request.get_json()
    get_req_keys = None
    get_req_keys_value_pair = None
    # Update only the provided fields
    for key, value in data.items():
        if key in validate_list:
            validate_status = True
            if get_req_keys is None:
                get_req_keys = key
                get_req_keys_value_pair = f'"{key}": "{value}"'
            else:
                get_req_keys = f"{get_req_keys}, {key}"
                get_req_keys_value_pair = f'{get_req_keys_value_pair}, "{key}": "{value}"'
  
    if validate_status is False:
        msg = {
            "code": 201,
            "message": str(validate_list)
        }
    else:
        try:
            if User.update_user( id, request_data.get('password1'), resource):
                msg = {
                        "code": 200,
                        "message": f"user detail(s) updated: {get_req_keys}",
                        # "data": 'f{instance_dict}'
                }
            else:
                msg = {
                    "code": 301,
                    "message": f"user detail(s) failed to updated.",
                    # "data": 'f{instance_dict}'
            }
        except Exception as e:
            msg = {
                    "code": 501,
                    "error :" : str(e),
                    "message": "server error." 
                }

    response = Response( json.dumps(msg), status=200, mimetype='application/json')
    return response  

@app.route('/v1/forget/password', methods=['PATCH'])
def forget_password():
    # Fetch the resource from your data source (e.g., database)
    request_data = request.get_json()
    resource = User.getUserByEmail(request_data.get("email"))
    validate_list = ["password1", "password2", "code", "email"]
    validate_status = False
    msg = {}
    if resource is None:
        return jsonify({ 'code': 404, 'error': 'Resource not found'}), 404
    elif Code.getCodeByOTP(request_data.get('code'), request_data.get('email') ) is None:
        return jsonify({ 'code': 403, 'error': 'Resource not found, check your email for the required code'}), 404
    # Get the data from the request
    data = request.get_json()
    get_req_keys = None
    get_req_keys_value_pair = None
    # Update only the provided fields
    for key, value in data.items():
        if key in validate_list:
            validate_status = True
            if get_req_keys is None:
                get_req_keys = key
                get_req_keys_value_pair = f'"{key}": "{value}"'
            else:
                get_req_keys = f"{get_req_keys}, {key}"
                get_req_keys_value_pair = f'{get_req_keys_value_pair}, "{key}": "{value}"'  
    if validate_status is False:
        msg = {
            "code": 201,
            "message": str(validate_list)
        }
    else:
        try:
            if User.update_email_user( request_data.get("email"), request_data.get('password1'), resource):
                msg = {
                        "code": 200,
                        "message": f"user detail(s) updated: {get_req_keys}",
                }
                Code.delete_email_code(request_data.get('code'), request_data.get('email') )
            else:
                msg = {
                    "code": 301,
                    "message": f"user detail(s) failed to updated.",
            }
        except Exception as e:
            msg = {
                    "code": 501,
                    "error :" : str(e),
                    "message": "server error." 
                }
    response = Response( json.dumps(msg), status=200, mimetype='application/json')
    return response  
       
@app.route('/v1/otp/email', methods=['POST'])
def send_notification():
    data = request.get_json()
    to_email = data['email']
    subject = 'Notification Subject'
    users = User.query.filter_by(email=to_email).first()
    try:
        if users:
            return 'User exist.'
        else:
            code = generate_random_code()
            render_html = render_template('email.html', code=code)
            Code.createCode(to_email, code, "OTP")
            if send_notification_email(to_email, subject, render_html):
                return jsonify({ 'code': 200, 'msg': 'Notification sent successfully'}), 200
            else:
                return 'Failed to send notification.'
    except Exception as e:
        return str(e)

@app.route('/v1/send/otp/email', methods=['POST'])
def send_otp():
    data = request.get_json()
    to_email = data['email']
    subject = 'Notification Subject'
    try:
        code = generate_random_code()
        render_html = render_template('email.html', code=code)
        Code.createCode(to_email, code, "OTP")
        if send_notification_email(to_email, subject, render_html):
            return jsonify({ 'code': 200, 'msg': 'Notification sent successfully'}), 200
        else:
            return 'Failed to send notification.'
    except Exception as e:
        return str(e)
@app.route('/')
def index():
    return render_template('/fileUpload.html')



@app.route('/school/<string:id>', methods=['GET', 'DELETE'])
@token_required
def school(id):
    if request.method == 'GET':
        try:
            request_data = School.get_school_by_id(id)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    elif request.method == 'DELETE':
        try:
            msg = {
                "code": 404,
                "message": 'Not found'
            }
            if School.delete_school(id):
                msg = {
                    "code": 200,
                    "message": 'Successful'
                }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
 
@app.route('/school', methods=['POST'])
def add_school():
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        # print("user_data ", user_data['file'] )
        user_email = user_data['email'] or None
        description = data.get('description')
        expected_applicantion = data.get('expected_applicantion')
        name = data.get('name')
        {k: v for k, v in data.items() if k not in ['name', 'expected_applicantion', 'description']}
        post_data = School.create_school(user_id, name, description, expected_applicantion, user_email)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': post_data.id,
                    'user_id': user_id,
                    'description': post_data.description,
                    'name': post_data.name,
                    'expected_applicantion': post_data.expected_applicantion,
                    'created_by': post_data.created_by,
                    'updated_by': post_data.updated_by,
                    'created_on': str(post_data.created_on),
                    'updated_on': str(post_data.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')


@app.route('/school/<string:id>', methods=['PATCH'])
def update_school(id):
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        user_email = user_data['email'] or None
        # Extracting the fields to be updated from the request data
        update_fields = {key: value for key, value in data.items() if key in ['name', 'description', 'school_id']}
        post_data = School.update_school(id, user_email, **update_fields)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': post_data.id,
                    'user_id': user_id,
                    'description': post_data.description,
                    'updated_by_id': user_email,
                    'created_by': post_data.created_by,
                    'updated_by': post_data.updated_by,
                    'created_on': str(post_data.created_on),
                    'updated_on': str(post_data.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')

@app.route('/student/<string:id>', methods=['GET', 'DELETE'])
@token_required
def student(id):
    if request.method == 'GET':
        try:
            request_data = Student.get_student_by_id(id)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    elif request.method == 'DELETE':
        try:
            msg = {
                "code": 404,
                "message": 'Not found'
            }
            if Student.delete_student(id):
                msg = {
                    "code": 200,
                    "message": 'Successful'
                }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
 
@app.route('/student', methods=['POST'])
def add_student():
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        user_email = user_data['email'] or None
        description = data.get('description')
        {k: v for k, v in data.items() if k not in ['description']}
        student = Student.create_student(user_id, description, user_email)
        if student:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': student.id,
                    'description': student.description,
                    'user_id': student.user_id,
                    'created_by': student.created_by,
                    'updated_by': student.updated_by,
                    'created_on': str(student.created_on),
                    'updated_on': str(student.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')

@app.route('/student/<string:id>', methods=['PATCH'])
def update_student(id):
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        user_email = user_data['email'] or None
        # Extracting the fields to be updated from the request data
        update_fields = {key: value for key, value in data.items() if key in ['name', 'description', 'school_id']}
        post_data = Student.update_student(id, user_email, **update_fields)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': post_data.id,
                    'user_id': user_id,
                    'description': post_data.description,
                    'updated_by_id': user_email,
                    'created_by': post_data.created_by,
                    'updated_by': post_data.updated_by,
                    'created_on': str(post_data.created_on),
                    'updated_on': str(post_data.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')


@app.route('/application/<string:id>', methods=['GET', 'DELETE'])
@token_required
def application(id):
    if request.method == 'GET':
        try:
            request_data = Application.get_application_by_id(id)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    elif request.method == 'DELETE':
        try:
            msg = {
                "code": 404,
                "message": 'Not found'
            }
            if Application.delete_application(id):
                msg = {
                    "code": 200,
                    "message": 'Successful'
                }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }

@app.route('/application-by-student/<string:id>', methods=['GET'])
@token_required
def applicationByStudent(id):
    # Extract query parameters
    page = request.args.get('page', default=1, type=int)
    per_page = request.args.get('per_page', default=10, type=int)
    if request.method == 'GET':
        try:
            request_data = Application.get_application_by_student_id(id, page, per_page)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data['data'],
                "pagination": request_data['pagination']
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    elif request.method == 'DELETE':
        try:
            msg = {
                "code": 404,
                "message": 'Not found'
            }
            if Application.delete_application(id):
                msg = {
                    "code": 200,
                    "message": 'Successful'
                }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }

@app.route('/application', methods=['POST'])
def add_application():
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        user_email = user_data['email'] or None
        description = data.get('description')
        programme_id = data.get('programme_id')
        student_id = Student.get_user_by_id(user_id)
        student_id = student_id.id or None

        {k: v for k, v in data.items() if k not in ['name', 'expected_applicantion', 'description']}
        post_data = Application.create_application(description, programme_id, student_id, user_email)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': post_data.id,
                    'user_id': user_id,
                    'description': post_data.description,
                    'student_id': post_data.student_id,
                    'programme_id': post_data.programme_id,
                    'created_by': post_data.created_by,
                    'updated_by': post_data.updated_by,
                    'created_on': str(post_data.created_on),
                    'updated_on': str(post_data.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')


@app.route('/application/<string:id>', methods=['PATCH'])
def update_application(id):
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        user_email = user_data['email'] or None
        # Extracting the fields to be updated from the request data
        update_fields = {key: value for key, value in data.items() if key in ['name', 'description', 'school_id']}
        post_data = Application.update_application(id, user_email, **update_fields)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': post_data.id,
                    'user_id': user_id,
                    'description': post_data.description,
                    'programme_id': post_data.programme_id,
                    'created_by': post_data.created_by,
                    'updated_by': post_data.updated_by,
                    'created_on': str(post_data.created_on),
                    'updated_on': str(post_data.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')


@app.route('/programme/<string:id>', methods=['GET', 'DELETE'])
@token_required
def programme(id):
    if request.method == 'GET':
        try:
            request_data = Programme.get_programme_by_id(id)
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    elif request.method == 'DELETE':
        try:
            request_data = Programme.delete_programme(id)
            msg = {
                "code": 200,
                "message": 'Successful'
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
 
@app.route('/programme', methods=['POST'])
def add_programme():
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        user_email = user_data['email'] or None
        description = data.get('description')
        school_id = data.get('school_id')
        name = data.get('name')
        {k: v for k, v in data.items() if k not in ['name', 'expected_applicantion', 'description']}
        post_data = Programme.create_programme(school_id, name, description, user_email)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': post_data.id,
                    'user_id': user_id,
                    'description': post_data.description,
                    'school_id': post_data.school_id,
                    'created_by': post_data.created_by,
                    'updated_by': post_data.updated_by,
                    'created_on': str(post_data.created_on),
                    'updated_on': str(post_data.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')

@app.route('/programme/<string:id>', methods=['PATCH'])
def update_programme(id):
    token = request.headers.get('Authorization')
    msg = {}
    try:
        token = token.split(" ")[1]        
        token_data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256']) or None
        data = request.get_json()
        user_id = token_data['id'] or None
        user_data = User.getUserById(user_id)
        user_email = user_data['email'] or None
        # Extracting the fields to be updated from the request data
        update_fields = {key: value for key, value in data.items() if key in ['name', 'description', 'school_id']}
        post_data = Programme.update_programme(id, user_email, **update_fields)
        if post_data:
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": {
                    'id': post_data.id,
                    'user_id': user_id,
                    'description': post_data.description,
                    'school_id': post_data.school_id,
                    'created_by': post_data.created_by,
                    'updated_by': post_data.updated_by,
                    'created_on': str(post_data.created_on),
                    'updated_on': str(post_data.updated_on)
                }
            }
        else:
            msg = {
                "code": 304,
                "message": 'Failed',
            }
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    except Exception as e:
        msg = {
            "code": 500,
            "message": 'Failed',
            "error": str(e)
        }
        return Response( json.dumps(msg), status=500, mimetype='application/json')


@app.route('/upload', methods=['POST'])
def upload():
    msg = {
        "code": 403,
        "message": 'Failed',
    }
    if request.method == 'POST':
        if fileUpload(request):
            msg = {
                "code": 200,
                "message": 'Successful',
            }
            return Response( json.dumps(msg), status=200, mimetype='application/json')
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    else:
        msg = {
            "code": 404,
            "message": 'Failed',
        }
        return Response( json.dumps(msg), status=404, mimetype='application/json')


@app.route('/upload/<string:id>', methods=['PATCH', 'GET'])
def uploadUpdate(id):
    if request.method == 'GET':
        return Fileupload.getFileById(id)
    if request.method == 'PATCH':
        return fileUpload(request, id)
    msg = {
        "code": 404,
        "message": 'Failed',
    }
    return Response( json.dumps(msg), status=404, mimetype='application/json')


@app.route('/file/delete/<string:id>', methods=['DELETE'])
def fileDelete(id):
    msg = {
        "code": 403,
        "message": 'Failed',
    }
    if request.method == 'DELETE':
        if Fileupload.delete_file(id):
            msg = {
                "code": 200,
                "message": 'Successful',
            }
            return Response( json.dumps(msg), status=200, mimetype='application/json')
        return Response( json.dumps(msg), status=200, mimetype='application/json')
    else:
        msg = {
            "code": 404,
            "message": 'Failed',
        }
        return Response( json.dumps(msg), status=404, mimetype='application/json')


if __name__ == "__main__":
    app.run(debug=True, port=5002)

