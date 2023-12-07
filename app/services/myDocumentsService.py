import concurrent.futures
import datetime
import os
import shutil
from pathlib import Path
from typing import List

from bson import ObjectId
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from app.config import Config
from app.models.mongoClient import MongoClient
from app.utils.common import Common
from app.utils.pipeline import PipelineStages
from app.utils.presentationmanager import PresentationManager
from app.utils.socket import socket_error, socket_info, socket_success


class MyDocumentsService:  

    @staticmethod
    def upload_document(logged_in_user, file, path):
        """
        The `upload_document` function uploads a file to a specified path, parses and inserts the
        document into a database, updates the virtual filename, and saves the file on disk or a cloud
        bucket.
        
        Args:
          logged_in_user: The logged_in_user parameter is an object that represents the currently logged
        in user. It contains information about the user, such as their ID, name, email, etc.
          file: The `file` parameter is the file object that is being uploaded. It contains the actual
        file data and metadata such as the filename.
          path: The `path` parameter represents the directory path where the document should be
        uploaded. It is a string that specifies the location within the file system or cloud storage
        where the document should be saved.
        
        Returns:
          a tuple containing two values: 1) an integer indicating the success or failure of the upload
        process (1 for success, 0 for failure), and 2) the inserted ID of the document in the database.
        """
        user_id = str(logged_in_user["_id"])
        if not user_id:
            raise Exception("User ID is missing")
        
        filename = Path(file.filename)
        new_path = Path(user_id) / Path(path)
        file_extension = filename.suffix.strip(".")
        new_path = str(new_path)
        print(f"New path: {new_path}")
        print(f"File: {filename}")
        print(f"File extension: {file_extension}")

        if file_extension not in ["pptx"]:
            socket_info(
                user_id,
                f"Skipping upload of {filename} due to incompatible file format",
            )
            return 0, None

        # Parse and insert document into database
        inserted_id = MyDocumentsService().parse_document(
            logged_in_user, file, new_path
        )

        if not inserted_id:
            socket_error(
                user_id,
                f"Failed to save {filename} to database due to some error...",
            )
            return 0, None

        # Update the virtual filename of the file based on its inserted ID
        update_response = MyDocumentsService().update_virtual_filename(
            inserted_id, file_extension
        )

        # Save file on disk or cloud bucket
        MyDocumentsService().save_file(file, inserted_id, logged_in_user, path)
        
        return 1, inserted_id           


    @staticmethod
    def upload_documents(logged_in_user, files, path):
        """
        The function `upload_documents` uploads multiple files to a specified path, using a
        ThreadPoolExecutor to execute the upload process concurrently, and updates the document
        vectorstore for each successfully uploaded file.
        
        Args:
          logged_in_user: The logged_in_user parameter is the user object of the currently logged in
        user. It contains information about the user, such as their ID, name, email, etc.
          files: The `files` parameter is a list of files that you want to upload. Each file should be
        in a format that can be processed by the `upload_document` method of the `MyDocumentsService`
        class.
          path: The `path` parameter is the directory path where the documents will be uploaded to.
        """
        user_id = str(logged_in_user["_id"])
        print("User:", user_id)
        
        # Create a ThreadPoolExecutor with a specified number of threads (e.g., 4)
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # Submit the function with arguments to the thread pool
            results = [executor.submit(MyDocumentsService().upload_document, logged_in_user, file, path) for file in files]
        
        # Getting function returns from all function calls from threadpool
        outputs = [result.result() for result in results]
        # All document _ids inserted
        uploaded_documents_ids = [output[1] for output in outputs if output[1]]
        # Number of documents successfully uploaded
        uploaded_documents_num = sum([output[0] for output in outputs])
        
        
        # Calculating number of documents successfully uploaded
        if uploaded_documents_num > 0:
            socket_success(
                user_id, f"Successfully uploaded {uploaded_documents_num} documents!"
            )

    @staticmethod
    def get_file_save_path(filename, user, path):
        """
        The function `get_file_save_path` returns the save path for a file based on the filename, user,
        and path provided.

        Args:
          filename: The name of the file that you want to save.
          user: The `user` parameter is the user ID or identifier. It is used to determine if the file
        is created by the user or if it is shared with the user.
          path: The `path` parameter is the path where the file should be saved. It is a string
        representing the directory structure where the file should be stored.

        Returns:
          the file save path.
        """
        # key = '_id'
        # user_id = user[key]
        file = MyDocumentsService().get_file_by_virtual_name(filename)
        file_created_by = file["createdBy"]["_id"]
        # print(
        #     f"File {filename} is created by {file_created_by} and the user is {user}. Path is {path}!"
        # )
        # Check if file is created by user
        if str(user) == str(file_created_by):
            user_folder_path = os.path.join(Config.USER_FOLDER, str(user))
            new_path = path[1:]
            # print("NEW PATH : " + new_path)
            if path != None:
                user_folder_path = os.path.join(user_folder_path, new_path)
                # print("USER FOLDER : ", user_folder_path)
            # if(folder_name != None):
            #     folder_save_path = os.path.join(user_folder_path, folder_name)
            # else:
            #     folder_save_path = user_folder_path
            file_save_path = os.path.join(user_folder_path, filename)
            # print("File save path to return : ", file_save_path)
        # If not then the file is shared
        else:
            replace_substring = "/" + str(file_created_by) + "/"
            user_folder_path = os.path.join(
                Config.USER_FOLDER, str(file_created_by)
            )
            file_root = file["root"]
            file_root = file_root.replace(replace_substring, "")
            # print("FILE ROOT: %s" % file_root)
            user_folder_path = os.path.join(user_folder_path, file_root)
            # print("USER: %s" % user_folder_path)
            file_save_path = os.path.join(user_folder_path, filename)
        return file_save_path

    @staticmethod
    def get_file_path(file, user_id):
        """
        The function `get_file_path` takes a file object and a user ID as input, and returns the file
        path based on the root folder and virtual file name.

        Args:
          file: The "file" parameter is a dictionary that contains information about a file. It has two
        keys: "root" and "virtualFileName".
          user_id: The user ID is a unique identifier for each user. It is used to identify the user's
        folder where the file is located.

        Returns:
          the file path as a string if it is successfully generated. If there is an exception, it will
        return None.
        """
        try:
            root = file["root"]
            root_folder_path = os.path.join(Config.USER_FOLDER, user_id)
            folder_substring = "/" + user_id + "/"
            file_name = file["virtualFileName"]
            if root == folder_substring:
                file_path = os.path.join(root_folder_path, file_name)
            else:
                new_root = root.replace(folder_substring, "")
                folder = os.path.join(root_folder_path, new_root)
                file_path = os.path.join(folder, file_name)

            # print("File path : ", file_path)

            return file_path

        except Exception as e:
            Common.exception_details("myDocumentsService.get_file_path", e)
            return None

    def parse_document(self, logged_in_user, file, new_path):
        """
        The function `parse_document` takes in a logged-in user, a file, and a new path, and based on
        the file extension, it calls different parsing functions to process the file and returns an
        inserted ID.

        Args:
          logged_in_user: The logged_in_user parameter is the user who is currently logged in and
        performing the document parsing operation.
          file: The `file` parameter is the file object that represents the document to be parsed. It is
        passed to the `parse_document` method as an argument.
          new_path: The `new_path` parameter is the path where the parsed document will be saved. It
        specifies the location where the parsed document will be stored after it has been processed.

        Returns:
          the variable "inserted_id".
        """
        try:
            filename = file.filename
            file_extension = filename.rsplit(".", 1)[-1]

            # PDF
            if file_extension == "pdf":
                print("Parsing pdf...")
                inserted_id = self._parse_pdf(file, filename, logged_in_user, new_path)

            # WORD
            elif file_extension == "doc" or file_extension == "docx":
                print("Parsing doc/docx...")
                inserted_id = self._parse_doc(file, filename, logged_in_user, new_path)

            # PPT
            elif file_extension == "pptx":
                print("Parsing pptx...")
                inserted_id = self._parse_pptx(file, filename, logged_in_user, new_path)

            # TXT
            elif file_extension == "txt":
                print("Parsing txt...")
                inserted_id = self._parse_text(file, filename, logged_in_user, new_path)

            else:
                print("Failed to parse invalid file format...")
                inserted_id = None

            return inserted_id

        except Exception as e:
            Common.exception_details("myDocumentsService.parse_document", e)
            return None

    def update_virtual_filename(self, file_id, file_extension):
        """
        Updates the virtual filename of the given file to "file_id.file_extension"
        """
        m_db = MongoClient.connect()

        virtual_filename = file_id + "." + file_extension
        response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].update_one(
            {"_id": ObjectId(file_id)}, {"$set": {"virtualFileName": virtual_filename}}
        )
        return response.modified_count

    def get_all_files(self, user_id, root):
        """
        Retrieves all the files uploaded by the user
        """
        m_db = MongoClient.connect()
        common_pipeline = MyDocumentsService._get_my_documents_pipeline()
        new_root = "/" + user_id + "/"

        if root and root != "/":
            new_root += root[1:]

        uploaded_documents = [
            PipelineStages.stage_match(
                {"createdBy._id": ObjectId(user_id), "root": new_root}
            )
        ] + common_pipeline

        shared_documents = [
            PipelineStages.stage_match(
                {"usersWithAccess": {"$in": [ObjectId(user_id)]}}
            ),
            PipelineStages.stage_lookup(
                Config.MONGO_USER_MASTER_COLLECTION,
                "createdBy._id",
                "_id",
                "userDetails",
            ),
            PipelineStages.stage_unwind("userDetails"),
            PipelineStages.stage_add_fields({"owner": "$userDetails.name"}),
            PipelineStages.stage_unset(["userDetails", "usersWithAccess"]),
        ] + common_pipeline

        # Use the facet pipeline stage to get both uploaded and shared documents
        pipeline = [
            PipelineStages.stage_facet(
                {"uploaded": uploaded_documents, "shared": shared_documents}
            )
        ]

        documents = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].aggregate(pipeline)
        return Common.cursor_to_dict(documents)

    def get_file(self, file_id):
        """
        The function `get_file` retrieves a file from a MongoDB database based on its ID.

        Args:
          file_id: The `file_id` parameter is the unique identifier of the file that you want to
        retrieve from the database.

        Returns:
          the first document that matches the given file_id.
        """
        m_db = MongoClient.connect()

        pipeline = [
            PipelineStages.stage_match({"_id": ObjectId(file_id)})
        ] + MyDocumentsService._get_my_documents_pipeline()

        response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].aggregate(pipeline)

        return Common.cursor_to_dict(response)[0]

    def rename_document(self, _id, rename_value, user_id):
        """
        The `rename_document` function renames a document (file or folder) in a database, and if the
        document is a folder, it also renames the corresponding folder in a cloud storage service (GCP)
        or in the system.

        Args:
          _id: The `_id` parameter is the unique identifier of the document that needs to be renamed. It
        is used to query the document from the database.
          rename_value: The `rename_value` parameter is the new name that you want to assign to the
        document.
          user_id: The `user_id` parameter is the unique identifier of the user who created the
        document.

        Returns:
          the number of modified documents in the database.
        """
        m_db = MongoClient.connect()
        query = {
            "_id": ObjectId(_id),
            "createdBy._id": ObjectId(user_id),
        }
        doc = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].find_one(query)
        # See if the document is a folder
        if doc["type"] == "Folder":
            root = doc["root"]

            # If we are on GCP then rename the folder in GCP
            if Config.GCP_PROD_ENV:
                pass
                # if root == "/" + str(user_id) + "/":
                #     folder_to_rename = root[1:] + doc["originalFileName"] + "/"
                #     new_folder_name = root[1:] + rename_value + "/"
                # else:
                #     folder_to_rename = root[1:] + "/" + doc["originalFileName"] + "/"
                #     new_folder_name = root[1:] + "/" + rename_value + "/"
                # # print("Folder to rename : ", folder_to_rename)
                # # print("New folder name: ", new_folder_name)
                
                # bucket = Production.get_users_bucket()
                # source_blob = bucket.blob(folder_to_rename)
                # destination_blob = bucket.blob(new_folder_name)
                # # Creating destination folder
                # destination_blob.upload_from_string("")
                # # print("Source blob : ", source_blob)
                # # print("Destination blob : ", destination_blob)

                # # list all blobs in source folder
                # blobs = bucket.list_blobs(prefix=folder_to_rename)
                # # print("Listing all blobs in source folder : ")
                # for blob in blobs:
                #     blob_name = str(blob.name)
                #     new_blob_name = blob_name.replace(folder_to_rename, new_folder_name)
                #     destination_blob = bucket.blob(new_blob_name)
                #     # Copy the file to the new new_blob_name
                #     blob_copy = bucket.copy_blob(blob, bucket, new_blob_name)
                #     # Delete the source blob after copying
                #     blob.delete()
                # old_root_value = "/" + folder_to_rename[:-1]
                # new_root_value = "/" + new_folder_name[:-1]
            # If we are on not on GCP then rename the folder in the system
            else:
                username_substring = "/" + user_id + "/"
                new_root = root.replace(username_substring, "")
                if root != username_substring:
                    new_root = new_root + "/"
                folder_to_rename = new_root + doc["originalFileName"]
                new_folder_name = new_root + rename_value
                user_folder_path = os.path.join(Config.USER_FOLDER, user_id)
                old_folder_path = os.path.join(user_folder_path, folder_to_rename)
                new_folder_path = os.path.join(user_folder_path, new_folder_name)

                try:
                    os.rename(old_folder_path, new_folder_path)
                except Exception as e:
                    print(f"Error renaming {folder_to_rename}")
                    print("================================================")
                    print(e)
                    print("================================================")
                    return None
                old_root_value = "/" + folder_to_rename
                new_root_value = "/" + new_folder_name
                # print("Old root value: " + old_root_value)
                # print("New root value: " + new_root_value)

            # Update the root of all the files and folders in this current folder
            children_records = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].find(
                {"root": {"$regex": old_root_value}}
            )
            res_count = 0
            for child in children_records:
                child_root = child["root"]
                updated_child_root = child_root.replace(old_root_value, new_root_value)
                update_child = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].update_one(
                    {
                        "_id": child["_id"],
                    },
                    {"$set": {"root": updated_child_root}},
                )
                res_count += update_child.modified_count

            # Update the original file name field for that record in the database
            response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].update_one(
                query,
                {"$set": {"originalFileName": rename_value}},
            )
            return response.modified_count + res_count
        # Since the document is a file, we need to update the database with the <new-name>.extension
        else:
            virtualFileName = doc["virtualFileName"]
            extension = virtualFileName[virtualFileName.rfind(".") + 1 :]
            # Update the original file name field for that record in the database
            response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].update_one(
                query,
                {"$set": {"originalFileName": rename_value + "." + extension}},
            )
            return response.modified_count

    def get_all_files_by_virtual_name(self, user_id, virtual_file_names):
        """
        The function retrieves all files with a given virtual file name for a specific user.

        Args:
          user_id: The user ID is a unique identifier for a user in the system. It is used to identify
        the user who created the documents.
          virtual_file_names: A list of virtual file names that you want to search for.

        Returns:
          the result of the query as a list of dictionaries.
        """
        m_db = MongoClient.connect()

        documents = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].find(
            {
                "createdBy._id": ObjectId(user_id),
                "virtualFileName": {"$in": virtual_file_names},
            }
        )

        return Common.cursor_to_dict(documents)

    def get_file_by_virtual_name(self, virtual_name):
        """
        The function retrieves a document from a MongoDB collection based on its virtual file name.

        Args:
          virtual_name: The virtual name is a parameter that represents the name of the file you want to
        retrieve from the database.

        Returns:
          the document that matches the given virtual name from the specified collection in the MongoDB
        database.
        """
        m_db = MongoClient.connect()

        document = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].find_one(
            {"virtualFileName": virtual_name}
        )

        return document

    def save_file(self, original_file, file_id, user, path):
        """
        The `save_file` function saves a file either to a cloud storage bucket or to a local folder,
        depending on the value of the `PRODUCTION_CHECK` variable.

        Args:
          original_file: The original file that needs to be saved.
          file_id: The `file_id` parameter is the unique identifier of the file that needs to be saved.
        It is used to retrieve information about the file from the database.
          user: The "user" parameter is a dictionary that contains information about the user. It likely
        includes details such as the user's ID, name, email, and other relevant information.
          path: The `path` parameter is a string that represents the path where the file should be
        saved. It can be an absolute path or a relative path.
        """
        key = "_id"
        user_id = user[key]
        # Get virtual filename from DB
        file = self.get_file(file_id)
        virtual_file_name = file["virtualFileName"]
        file_root = file["root"]

        if Config.GCP_PROD_ENV:
            pass
            # # print("PATH : ", path)
            # # print("Original file :", original_file)

            # if path == "/":
            #     folder_name = str(user_id) + path
            # else:
            #     folder_name = file_root[1:] + "/"

            # bucket = Production.get_users_bucket()
            # file_blob = bucket.blob(folder_name + virtual_file_name)

            # # finding the file extension
            # extension = virtual_file_name[virtual_file_name.rfind(".") + 1 :]

            # original_file.stream.seek(0)
            # if extension == "pdf":
            #     file_blob.upload_from_string(
            #         original_file.read(), content_type="application/pdf"
            #     )
            # else:
            #     file_blob.upload_from_string(original_file.read())

            # print(f"File {virtual_file_name} uploaded to {folder_name} successfully.")
            # print("Path sent to get_file_save_path: ", path)

        else:
            # Ensure that the user image upload folder exists
            folder_path = os.path.join(Config.USER_FOLDER, str(user_id))
            os.makedirs(folder_path, exist_ok=True)

            # Save file
            file_save_path = self.get_file_save_path(virtual_file_name, user_id, path)
            print(type(original_file))
            # blob = original_file.read()
            # Path(file_save_path).write_bytes(blob)
            original_file.stream.seek(0)
            original_file.save(file_save_path)

            print("Saved file!")


    @staticmethod
    def _get_my_documents_pipeline():
        """Common My Documents pipeline

        Returns:
            list: Common My Documents pipeline
        """

        my_documents_pipeline = [
            PipelineStages.stage_add_fields(
                {
                    "createdBy._id": {"$toString": "$createdBy._id"},
                    "createdOn": {"$dateToString": {"date": "$createdOn"}},
                    "_id": {"$toString": "$_id"},
                    "virtualFileName": "$virtualFileName",
                    "usersWithAccess": {
                        "$map": {
                            "input": "$usersWithAccess",
                            "as": "user",
                            "in": {"$toString": "$$user"},
                        }
                    },
                }
            ),
            PipelineStages.stage_unset(["embeddings", "highlightsSummary"]),
        ]

        return my_documents_pipeline

    @staticmethod
    def _create_my_document_db_struct(title, description, filename, user, root):
        """
        The function `_create_my_document_db_struct` creates a document structure for a file in a
        document database.

        Args:
          title: The title of the document.
          description: The "description" parameter is a string that represents the description of the
        document. It provides additional information or details about the document.
          filename: The `filename` parameter is the name of the file that you want to create a document
        database structure for.
          user: The "user" parameter is a dictionary that represents the user who is creating the
        document. It contains information about the user, such as their ID and a reference to the user
        object.
          root: The "root" parameter is used to specify the root directory or folder where the document
        will be stored. If no root directory is provided (root == ""), the document will be stored in
        the root directory ("/").

        Returns:
          a document (doc) with various fields such as title, description, itemizedSummary,
        highlightsSummary, originalFileName, virtualFileName, createdBy, createdOn, embeddings, type,
        root, usersWithAccess, and storedOnCloud.
        """
        if root == "":
            root = "/"

        m_db = MongoClient.connect()
        # Check if the file with the same name already exists in the collection
        existing_files = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].find(
            {"root": str(root)},
            {"_id": 0, "originalFileName": 1}
        )

        # Create a set of existing filenames for efficient lookup
        existing_filenames = set(file["originalFileName"] for file in existing_files)

        # If the filename already exists, increment the index count
        index = 1
        new_filename = filename
        while new_filename in existing_filenames:
            file_name_without_extension, file_extension = os.path.splitext(filename)
            print("File name without extension:", file_name_without_extension)
            new_filename = f"{file_name_without_extension}({index}){file_extension}"
            index = index + 1

        doc = {
            "title": title,
            "description": description,
            "itemizedSummary": "",  # update when itemized summary of this record is generated
            "highlightsSummary": "",  # update when highlight summary of this record is generated
            "originalFileName": str(new_filename),  # Use the unique filename
            "virtualFileName": "",
            "createdBy": {"_id": ObjectId(user["_id"]), "ref": "user"},
            "createdOn": datetime.datetime.utcnow(),
            "embeddings": None,
            "type": "File",
            "root": root,
            "usersWithAccess": [],
        }

        return doc

    def _parse_pptx(self, file, filename, user, root):
        """
        The _parse_pptx function extracts content from the file and inserts a new record corresponding to the file.
            Args:
                file (file storage) : The file to be parsed
                original_filename (str) : The name of this file to be parsed
                user (dict): Identifies the user uploading the file.

        Args:
            self: Represent the instance of the class
            file : The file to be parsed
            original_filename (str) : The name of this file to be parsed
            user (str): Corresponds to the user uploading the file.

        Returns:
            The Objectid of the newly inserted record
            :param user:
            :param file:
            :param filename:

        """

        m_db = MongoClient.connect()


        ppt = PresentationManager(file=file)
        slide_texts = ppt.extract_all_text()
        title = ppt.title
        ppt_content = "\n".join([slide["content"] for slide in slide_texts if slide["content"]])

        file_data = MyDocumentsService._create_my_document_db_struct(
            title, ppt_content, filename, user, root
        )
        # print(file_data)
        response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].insert_one(file_data)

        if response:
            return str(response.inserted_id)

        return None

    def _parse_text(self, file, filename, user, root):
        """
        The _parse_doc function extracts content from the file and inserts a new record corresponding to the file.
            Args:
                file (file storage) : The file to be parsed
                original_filename (str) : The name of this file to be parsed
                user (dict): Identifies the user uploading the file.

        Args:
            self: Represent the instance of the class
            file : The file to be parsed
            original_filename (str) : The name of this file to be parsed
            user (str): Corresponds to the user uploading the file.

        Returns:
            The ObjectId of the newly inserted record
            :param user:
            :param file:
            :param filename:

        """

        m_db = MongoClient.connect()
        print(file)

        try:
            title = file.readline().decode(
                "utf-8"
            )  # Decode the bytes into a string using the appropriate encoding
            content = file.read().decode("utf-8")
            name, extension = os.path.splitext(filename)
            # print(f"name {name}, ext {extension}, file {filename}")
            if (
                title == "" or title == "\r\n"
            ):  # if there is a space or new line here \r\n will match the new line
                title = name

            file_data = MyDocumentsService._create_my_document_db_struct(
                title, content, filename, user, root
            )
            print(file_data)
            response = m_db[Config.MONGO_DOCUMENT_MASTER_COLLECTION].insert_one(
                file_data
            )

            if response:
                return str(response.inserted_id)

        except Exception as e:
            print("An error occurred:", e)
            return None
