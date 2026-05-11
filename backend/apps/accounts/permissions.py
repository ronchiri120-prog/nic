"""accounts/permissions.py — Role-Based Permission Classes"""
from rest_framework.permissions import BasePermission
from .models import User

R = User.Role  # shorthand


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == R.SUPER_ADMIN or request.user.is_superuser
        )


class IsRegionalManagerOrAbove(BasePermission):
    """RM, Super Admin — cross-branch oversight"""
    ALLOWED = {R.SUPER_ADMIN, R.RM}
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class IsBranchManagerOrAbove(BasePermission):
    ALLOWED = {R.SUPER_ADMIN, R.BRANCH_MANAGER, R.RM, R.OPERATIONS}
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class IsLoanOfficerOrAbove(BasePermission):
    """Anyone who can work with loans/customers"""
    ALLOWED = {
        R.SUPER_ADMIN, R.ADMIN, R.BRANCH_MANAGER, R.LOAN_OFFICER, R.IDC,
        R.RM, R.OPERATIONS, R.BDO, R.PAYMENT_OFFICER, R.DISBURSEMENT_OFFICER,
        R.COLLECTIONS_MGR, R.EDC_MANAGER, R.COLLECTIONS, R.FA_MANAGER,
        R.VERIFICATION_TEAM, R.FINANCE, R.CC_MANAGER, R.FRONT_OFFICE,
        R.TECH,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class CanCreateLead(BasePermission):
    """BDO can create leads; everyone above can too"""
    ALLOWED = {
        R.SUPER_ADMIN, R.ADMIN, R.BRANCH_MANAGER, R.LOAN_OFFICER, R.IDC,
        R.RM, R.OPERATIONS, R.BDO, R.CALL_CENTRE, R.CC_MANAGER,
        R.FRONT_OFFICE, R.FINANCE, R.TECH,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class CanConvertLead(BasePermission):
    """BDO and above can convert leads"""
    ALLOWED = {
        R.SUPER_ADMIN, R.BRANCH_MANAGER, R.LOAN_OFFICER, R.IDC,
        R.RM, R.OPERATIONS, R.BDO,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class IsAccountantOrAbove(BasePermission):
    ALLOWED = {R.SUPER_ADMIN, R.FINANCE, R.RM}
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class CanApproveLoan(BasePermission):
    """Branch Managers, RM, and Operations can approve loans after verification"""
    ALLOWED = {
        R.SUPER_ADMIN, R.BRANCH_MANAGER, R.RM, R.OPERATIONS,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class CanUploadPayment(BasePermission):
    """Privileged payment upload — Tech, Operations (HOP), RM (GM), Admin, Collections Manager"""
    ALLOWED = {
        R.SUPER_ADMIN, R.RM, R.OPERATIONS, R.TECH, R.COLLECTIONS_MGR,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class IsCollectionsOrAbove(BasePermission):
    """Collections team — agents, manager, EDC, and above"""
    ALLOWED = {
        R.SUPER_ADMIN, R.BRANCH_MANAGER, R.RM,
        R.COLLECTIONS, R.COLLECTIONS_MGR, R.EDC_MANAGER, 
        R.EXTERNAL_DEBT_COLLECTOR, R.FIELD_AGENT,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class IsMarketingOrAbove(BasePermission):
    """CRM team access"""
    ALLOWED = {
        R.SUPER_ADMIN, R.RM, R.BDO, R.CC_MANAGER, R.CALL_CENTRE,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )


class IsVerificationTeam(BasePermission):
    """Verification team — loan document verification, cross-branch customer access, reference checks"""
    ALLOWED = {
        R.SUPER_ADMIN, R.VERIFICATION_TEAM,
    }
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in self.ALLOWED or request.user.is_superuser
        )
