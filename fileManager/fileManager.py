import mimetypes
from Model import Fileupload
import os


def fileUploadManager(request, *args):
    if 'cert' not in request.files:
        return 'No cert part in the request'
    file = request.files['cert']
    if file.filename == '':
        return 'No selected file'
    try:
        if request.method == 'POST':
            data_object = Fileupload.createFile(file.filename, file.filename, 'test')
            print("data_object ", data_object.id)
            # save it to the folder
            upload_folder = 'static/uploads'
            file.save( upload_folder + '/' + file.filename)
            # Determine the file type
            file_type, encoding = mimetypes.guess_type(os.path.join(upload_folder, file.filename))
            new_filename = data_object.id + '.' + file_type.split('/')[1]
            file_path = os.path.join(upload_folder, new_filename)
            os.rename(os.path.join(upload_folder, file.filename), file_path)
            return {'message': 'File uploaded successfull', 'statuscode': 200}

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
                file_data['statuscode'] = 200
                return file_data

    except Exception as e:
        return f'{str(e)} file'

