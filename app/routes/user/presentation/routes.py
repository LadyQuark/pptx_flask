from flask import Blueprint, request

from app.services.myDocumentsService import MyDocumentsService
from app.utils.common import Common
from app.utils.messages import Messages
from app.utils.response import Response

presentation = Blueprint("presentation", __name__, url_prefix="/api/presentation")
TEST_USER = {"_id": "65700cee327beccab31fc13b"}

@presentation.route("/upload-documents", methods=["POST"])
def upload_documents():
    try:
        logged_in_user = TEST_USER
        files = request.files.getlist("files[]")
        path = request.form.get("path", "/ppt")

        # Upload files
        MyDocumentsService.upload_documents(logged_in_user, files, path)
        
        return Response.custom_response([], Messages.OK_FILE_UPLOAD_STARTED, True, 200)

    except Exception as e:
        Common.exception_details("mydocuments.py : upload_documents", e)
        return Response.server_error()




@presentation.route("/download/<ppt_name>", methods=["GET"])
def download_documents():
    try:
        logged_in_user = TEST_USER

        #TODO

    except Exception as e:
        Common.exception_details("mydocuments.py : download_documents", e)
        return Response.server_error()

@presentation.route("/search/generate", methods=["GET"])
def search_and_generate():
    try:
        logged_in_user = TEST_USER

        #TODO

    except Exception as e:
        Common.exception_details("mydocuments.py : search_and_generate", e)
        return Response.server_error()

