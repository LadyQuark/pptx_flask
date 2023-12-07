"""
    Common MongoDB pipeline stages
"""


class PipelineStages:

    @staticmethod
    def stage_find_all():
        """Returns all values

        Returns:
            dict: Match pipeline stage
        """

        stage_match = {
            "$match": {}
        }

        return stage_match

    @staticmethod
    def stage_match(fields):
        """Match pipline stage

        Args:
            fields (dict): All fields to match

        Returns:
            dict: Match pipeline stage
        """
        stage_match = {
            "$match": fields
        }

        return stage_match

    @staticmethod
    def stage_skip(offset):
        """Skip pipeline stage

        Args:
            offset (int): Skip value

        Returns:
            dict: Skip pipeline stage
        """

        stage_skip = {
            "$skip": offset
        }

        return stage_skip

    @staticmethod
    def stage_limit(limit):
        """Limit pipeline stage

        Args:
            limit (int): Limit value

        Returns:
            dict: Limit pipeline stage
        """

        stage_limit = {
            "$limit": limit
        }

        return stage_limit

    @staticmethod
    def stage_change_root(new_root):
        """Change root pipeline stage

        Args:
            new_root (string): Root name

        Returns:
            dict: Change root pipeline stage
        """

        stage_change_root = {
            "$replaceRoot": {
                "newRoot": "$" + new_root
            }
        }

        return stage_change_root

    @staticmethod
    def stage_add_fields(new_fields_dict):
        """Add field pipeline stage

        Args:
            new_fields_dict (dict): All new fields and their values

        Returns:
            dict: Add field pipeline stage
        """

        stage_add_fields = {
            "$addFields": new_fields_dict
        }

        return stage_add_fields

    @staticmethod
    def stage_lookup(target_collection, local_field, foreign_field, lookup_name):
        """Lookup pipeline stage

        Args:
            target_collection (string): Target collection to lookup
            local_field (string): local field name to match
            foreign_field (string): foreign field to match to localField
            lookup_name (string): Name of lookup

        Returns:
            dict: Lookup stage
        """

        stage_lookup = {
            "$lookup": {
                "from": target_collection,
                "localField": local_field,
                "foreignField": foreign_field,
                "as": lookup_name
            }
        }

        return stage_lookup

    @staticmethod
    def stage_lookup_by_pipeline(target_collection, local_field, foreign_field, lookup_name, pipeline):

        """
            The stage_lookup_by_pipeline function takes in the following parameters:
                target_collection (str): The name of the collection to be looked up.
                local_field (str): The field in the current collection that will be used as a reference for lookup.
                foreign_field (str): The field in the target collection that will be used as a reference for lookup.  This should match with local_field, but is not required to do so.  If it does not match, then this function can still work by using $project stages before and after this stage to rename fields appropriately.
                lookup_name (str): A

            Args:
                target_collection: Specify the collection that is being looked up
                local_field: Specify the field in the current collection to match against
                foreign_field: Specify which field in the target collection to match against
                lookup_name: Name the field in which the results of the lookup will be stored
                pipeline: Specify the pipeline that will be used to filter the documents in target_collection

            Returns:
                A $lookup stage with a pipeline argument

        """
        stage_lookup_by_pipeline = {
            "$lookup": {
                "from": target_collection,
                "let": {"id": "$" + local_field},
                "pipeline": [
                                {"$match": {"$expr": {"$eq": ["$" + foreign_field, "$$id"]}}}
                            ] + pipeline,
                "as": lookup_name
            }
        }

        return stage_lookup_by_pipeline

    @staticmethod
    def stage_unwind(lookup_name, preserve_null_and_empty=False):
        """Unwind pipeline stage

        Args: lookup_name (string): Name of lookup preserve_null_and_empty (bool, optional): Flag to preserve null
        and empty join fields or remove them. Defaults to False.

        Returns:
            dict: Unwind stage
        """

        stage_unwind = {
            "$unwind": {
                "path": "$" + lookup_name,
                "preserveNullAndEmptyArrays": preserve_null_and_empty
            }
        }

        return stage_unwind

    @staticmethod
    def stage_project(projection_keys=None):
        """Projection pipeline stage

        Args:
            projection_keys (list, optional): All keys which are to be projected.
                If None, all keys are projected.

        Returns:
            dict: Projection stage
        """

        projection_fields = {}

        if projection_keys is not None:
            # If projection_keys is specified, include only those fields
            for key in projection_keys:
                projection_fields[key] = 1

        stage_project = {
            "$project": projection_fields
        }

        return stage_project

    @staticmethod
    def stage_group_by(expression, groups):
        """Group by pipeline stage

        Args:
            expression (string): Expression for filtering out items for grouping
            groups (list): [
                <outputField1>: { <accumulator1>: <expression1> },
                <outputField2>: { <accumulator2>: <expression2> }.....
            ]

        Returns:
            dict: Group by stage
        """

        # { $group: {
        #     _id: <expression>,
        #     <outputField1>: { <accumulator1>: <expression1> },
        #     <outputField2>: { <accumulator2>: <expression2> },
        #     ...
        # }}

        group_dict = {
            "_id": expression
        }

        for group in groups:
            field = group["field"]
            accumulator = group["accumulator"]
            expression = group["expression"]

            group_dict[field] = {}
            group_dict[field][accumulator] = expression

        stage_group_by = {
            "$group": group_dict
        }

        return stage_group_by

    @staticmethod
    def stage_union_with(collection_name, pipeline=None):
        """unionWith pipeline stage

        Args:
            collection_name (string): Name of collection to perform union with
            pipeline (list, optional): Pipeline to filter on target collection. Defaults to [].

        Returns:
            dict: unionWith pipeline stage
        """

        # { $unionWith: { coll: "<collection>", pipeline: [ <stage1>, ... ] } }

        if pipeline is None:
            pipeline = []
        stage_union_with = {
            "$unionWith": {
                "coll": collection_name,
                "pipeline": pipeline
            }
        }

        return stage_union_with

    @staticmethod
    def stage_sort(sort_dict):
        """Sort pipeline stage

        Args:
            sort_dict (dict): Sorting dictionary

        Returns:
            dict: Sort pipeline stage
        """

        stage_sort = {
            "$sort": sort_dict
        }

        return stage_sort

    @staticmethod
    def stage_facet(facet_dict):
        """Facet pipeline stage

        Args:
            facet_dict (dict): Dictionary containing facets to perform

        Returns:
            dict: Facet stage
        """

        # { $facet: {
        #     <outputField1>: [ { <stage1> }, { <stage2> }, ... ],
        #     <outputField2>: [ { <stage1> }, { <stage2> }, ... ],
        #     ...
        #   }
        # }

        stage_facet = {
            "$facet": facet_dict
        }

        return stage_facet

    @staticmethod
    def stage_unset(unset_list):
        """
            The stage_unset function takes a list of fields to be unset as an argument and returns a dictionary with the $unset operator.

            Args:
                unset_list: Pass in a list of fields to be unset

            Returns:
                A dictionary that can be used to update a mongodb document

        """

        stage_unset = {
            "$unset": unset_list
        }

        return stage_unset

    @staticmethod
    def stage_group(group_dict):

        """
            The stage_group function takes a dictionary as an argument and returns a MongoDB aggregation pipeline stage.
            The purpose of this function is to make it easier to create the $group stage in the pipeline.


            Args:
                group_dict: Specify the fields to group by and the

            Returns:
                A $group stage
        """

        stage_group = {
            "$group": group_dict
        }

        return stage_group
