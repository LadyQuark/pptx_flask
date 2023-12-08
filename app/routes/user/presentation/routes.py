from flask import Blueprint, request, send_file

from app.services.elasticService import ElasticService
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

        if not files:
            return Response.missing_required_parameter("Files")

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
        request_params = request.args.to_dict()

        if "query" not in request_params:
            return Response.missing_required_parameter("query")
        query = str(request_params.get("query", ""))    

        results = ElasticService().search_in_index_all(
            query=query, 
            user_id=logged_in_user["_id"]
            )
        
        file_path = MyDocumentsService().generate_pptx_from_search(
            elastic_results=results, 
            user_id=logged_in_user["_id"], 
            query=query
            )
        if not file_path:
            return Response.server_error()
        
        download_name = Common.get_valid_filename(f"{query}.pptx")
        
        return send_file(
            file_path, as_attachment=True, download_name=download_name
        )

    except Exception as e:
        Common.exception_details("mydocuments.py : search_and_generate", e)
        return Response.server_error()


@presentation.route("/search", methods=["GET"])
def search_documents():
    try:
        logged_in_user = TEST_USER
        request_params = request.args.to_dict()

        if "query" not in request_params:
            return Response.missing_required_parameter("query")
        query = str(request_params.get("query", ""))    

        resp = ElasticService().search_in_index(
            query=query, 
            user_id=logged_in_user["_id"]
            )
        total = resp['total']['value']
        print("")
        results = [item['_source'] for item in resp['hits']]
        
        if len(results) > 0:
            return Response.custom_response(
                results, Messages.OK_KI_RETRIEVAL, True, 200
            )

    except Exception as e:
        Common.exception_details("mydocuments.py : search_and_generate", e)
        return Response.server_error()

