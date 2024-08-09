import mimetypes
from Model import Fileupload
import os
import boto3
from dotenv import dotenv_values

get_env = dotenv_values(".env")  
# Initialize a session using your access keys
s3 = boto3.client(
    's3',
    aws_access_key_id=get_env['AWS_ACCESS_KEY_ID']  ,
    aws_secret_access_key=get_env['AWS_SECRET_ACCESS_KEY']  ,
    region_name=get_env['REGION_NAME']  
)
# Initialize S3 client
# s3 = session.client('s3')

#    - Identification Document (Passport, ID Card)
#    - Previous Credential Evaluation Reports (if any)
#    - Letters of Recommendation (if applicable)
 
def fileUploadManager(request, user_id, *args):
    file = ""
    issued_date = ""
    slug = ''
    # if 'cert' or 'photo' not in request.files:
    #     return {'message': 'No cert part in the request', 'status': False} 
    print("photo", request.form.get('photo'))  
    if 'photo' in request.files:     
        file = request.files['photo']
    elif 'cert' in request.files:
        file = request.files['cert']
   

    print("file", file)
    if file.filename == '':
        return {'message': 'No selected file', 'status': False}
    try:
        if request.method == 'POST':
            doc_type = ""
            if str(request.form.get('type')) == "0":
                doc_type = "Photo"
                slug = doc_type
                issued_date = None
            if str(request.form.get('type')) == "1":
                doc_type = "Certificate"
                slug = request.form.get('slug')
                issued_date = request.form.get('issued_date')
            if str(request.form.get('type')) == "2":
                doc_type = "Transcript"
                slug = request.form.get('slug')
                issued_date = request.form.get('issued_date')
            if str(request.form.get('type')) == "3":
                doc_type = "Identification Document"
                slug = "Identification Document"
                issued_date = request.form.get('issued_date')
            if str(request.form.get('type')) == "4":
                doc_type = "Evaluation Report"
                slug = "Identification Document"
                issued_date = request.form.get('issued_date')
            if str(request.form.get('type')) == "5":
                doc_type = "Letter of Recommendation"
                slug = "Identification Document"
                issued_date = request.form.get('issued_date')
                
            doc_format = file.content_type.split('/')[1]
            data_object = Fileupload.createFile(file.filename, file.filename, doc_type, doc_format, user_id, issued_date, slug)
            # save it to the folder
            upload_folder = 'static/uploads'
            file.save( upload_folder + '/' + file.filename)
            # Determine the file type
            file_type, encoding = mimetypes.guess_type(os.path.join(upload_folder, file.filename))
            new_filename = data_object.id + '.' + file_type.split('/')[1]
            file_path = os.path.join(upload_folder, new_filename)
            os.rename(os.path.join(upload_folder, file.filename), file_path)

            # S3
            bucket_name = 'league-ms-s3'
            local_file_path = file_path
            s3_object_name = new_filename
            # Upload the file to S3
            try:
                s3.upload_file(local_file_path, bucket_name, s3_object_name, 
                ExtraArgs={
                    'ContentType': str(file_type),
                    'ContentDisposition': 'inline'
                } )
                os.remove(local_file_path)  # Clean up the local file after upload
                return {'message': 'File uploaded successfull', 'status': True}
            except Exception as e:
                return {'message': 'File uploaded failed.', 'status': False, 'error': str(e)}

        if request.method == 'PATCH':
            for arg in args:
                file_data = Fileupload.updateFile(file.filename, file.filename, 'test', arg)
                # save it to the folder
                upload_folder = 'static/uploads'
                file.save( upload_folder + '/' + file.filename)
                # Determine the file type
                file_type, encoding = mimetypes.guess_type(os.path.join(upload_folder, file.filename))
                new_filename = arg + '.' + file_type.split('/')[1]
                file_path = os.path.join(upload_folder, new_filename)
                os.rename(os.path.join(upload_folder, file.filename), file_path)
                file_data['message'] = 'File uploaded successfully'
                return file_data

    except Exception as e:
        return {'message': 'File uploading failed', 'status': False, 'error': str(e)}

