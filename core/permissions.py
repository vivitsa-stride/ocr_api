from rest_framework import permissions


class DocumentAccessPermission(permissions.BasePermission):
    """
    Global permission to check if user has access to the object
    """
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user
