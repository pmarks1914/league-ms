from crypt import methods
import uuid
from flask import Flask, jsonify, request, Response, render_template
import requests, json
from Helper.helper import generate_random_code
from fileManager.fileManager import fileUpload
#import geocoder
from Model import School, Student, User, Code, db, Fileupload
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
app.config['SECRET_KEY'] = get_env['SECRET_KEY']        



@app.route('/test', methods=['POST'])
def testd():
    try:
        print((request.json)['test'] )
        # user = User.getAllUsers((request.json)['email'])

        msg = {
            "code": 200,
            "helpString": 'Successful'
        }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response    
    except Exception as e:
        # print(e)
        return {"tes": str(e)}

@app.route('/v1/callback/mfs', methods=['POST'])
def callbackMfs():
    try:
        request_data = request.json
        # print("mfs callback >>> ", request_data )
        msg = {
            "code": 200,
            "helpString": 'Successful',
            "data": request_data
        }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response 
    except Exception as e:
        # print(e)
        return {"tes": str(e)}

@app.route('/login', methods=['POST'])
def get_token():
    request_data = request.get_json()
    password_hashed = hashlib.sha256((request_data.get('password')).encode()).hexdigest()
    match = User.username_password_match(request_data.get('email'), password_hashed)
    if match is not None:
        expiration_date = datetime.datetime.utcnow() + datetime.timedelta(hours=6)
        token = jwt.encode({'exp': expiration_date}, app.config['SECRET_KEY'], algorithm='HS256')
        msg = { "user": match, "access_key": jwt.decode( token, app.config['SECRET_KEY'], algorithms=['HS256'] ), "token": token }
        response = Response( json.dumps(msg), status=200, mimetype='application/json')
        return response 
    else:
        return Response('', 401, mimetype='application/json')
    
def token_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        token = token.split(" ")[1]        
        if not token:
            return jsonify({'error': 'Token is missing', 'status': 401}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            return f(*args, **kwargs)
        except ExpiredSignatureError :
            return jsonify({'error': 'Token has expired', 'status': 401}), 401
        except InvalidTokenError:
            return jsonify({'error': 'Invalid Token', 'status': 401}), 401
        except Exception as e:
            return jsonify({'error': str(e), 'status': 401}), 401
    return wrapper

@app.route('/user/<string:id>', methods=['GET'])
@token_required
def user(id):
    if request.method == 'GET':
        try:
            request_data = User.getUserById(id)
            # print("mfs callback >>> ", request_data )
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            # print(e)
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
        
@app.route('/v1/registration/', methods=['POST'])
def add_user_registration():
    request_data = request.get_json()
    _first_name = request_data.get('first_name')
    msg = {}
    # print("fff")
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

        print(User.query.filter_by(email=request_data.get('email')).first())
        if User.query.filter_by(email=request_data.get('email')).first() is not None:
            msg = {
                "code": 202,
                "error": "user already registtered",
                "helpString": 'Data passed" }'
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response
        else:
            User.createUser(_first_name, _last_name, _other_name, _password, _email, _description, _role, _address)
            # print(json.dumps(user))
            invalidUserOjectErrorMsg = {
                "code": 200,
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
  
@app.route('/v1/password/<string:id>', methods=['PATCH'])
def update_password(id):
    # Fetch the resource from your data source (e.g., database)
    request_data = request.get_json()
    resource = User.getUserById(id, request_data.get('email'))
    print(Code.getCodeByOTP(request_data.get('code')))
    validate_list = ["id", "password1", "password2", "code", "email"]
    validate_status = False
    msg = {}
    if resource is None:
        return jsonify({ 'code': 404, 'error': 'Resource not found'}), 404
    elif Code.getCodeByOTP(request_data.get('code')) is None:
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
  
    # print(json.dumps(get_req_keys_value_pair))
    if validate_status is False:
        msg = {
            "code": 201,
            "msg": str(validate_list)
        }
    else:
        try:
            if User.update_user( id, request_data.get('password1'), resource):
                msg = {
                        "code": 200,
                        "msg": f"user detail(s) updated: {get_req_keys}",
                        # "data": 'f{instance_dict}'
                }
            else:
                msg = {
                    "code": 301,
                    "msg": f"user detail(s) failed to updated",
                    # "data": 'f{instance_dict}'
            }
        except Exception as e:
            msg = {
                    "code": 501,
                    "error :" : str(e),
                    "msg": "server error" 
                }
    # print("resource", resource)

    response = Response( json.dumps(msg), status=200, mimetype='application/json')
    return response  
      
@app.route('/v1/otp/email', methods=['POST'])
def send_notification():
    data = request.get_json()
    to_email = data['email']
    # print(to_email)
    subject = 'Notification Subject'
    users = User.query.filter_by(email=to_email).first()
    # print(users.id)
    try:
        if users:
            code = generate_random_code()
            render_html = render_template('email.html', code=code)
            Code.createCode(to_email, code, "OTP")
            if send_notification_email(to_email, subject, render_html):
                return jsonify({ 'code': 200, 'msg': 'Notification sent successfully'}), 200
            else:
                return 'Failed to send notification.'
        else:
            return 'User does not exist'
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    return render_template('/fileUpload.html')



@app.route('/school/<string:id>', methods=['GET'])
@token_required
def school(id):
    if request.method == 'GET':
        try:
            request_data = School.get_school_by_id(id)
            # print("mfs callback >>> ", request_data )
            msg = {
                "code": 200,
                "message": 'Successful',
                "data": request_data
            }
            response = Response( json.dumps(msg), status=200, mimetype='application/json')
            return response 
        except Exception as e:
            # print(e)
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
 
@app.route('/student/<string:id>', methods=['GET'])
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
            # print(e)
            return {"code": 203, "message": 'Failed', "error": str(e)}
    else:
        return {"code": 400, "message": 'Failed' }
 

@app.route('/upload', methods=['POST'])
def upload():
    return fileUpload(request)

@app.route('/upload/<string:id>', methods=['PATCH', 'GET'])
def uploadUpdate(id):
    if request.method == 'GET':
        return Fileupload.getFileById(id)
    if request.method == 'PATCH':
        return fileUpload(request, id)

@app.route('/file/delete/<string:id>', methods=['DELETE'])
def fileDelete(id):
    if request.method == 'DELETE':
        return Fileupload.delete_file(id)
    else:
        pass

if __name__ == "__main__":
    app.run(debug=True, port=5002)