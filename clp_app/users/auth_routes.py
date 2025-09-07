from flask import Blueprint, render_template
from clp_app.users.decorators import role_required
from flask_login import login_user, logout_user, login_required, current_user

auth_bp = Blueprint("auth", __name__, url_prefix='/auth')


@auth_bp.route("/login")
def login_route():
    return render_template()


@auth_bp.route("/logout")
def logout_route():
    logout_user()
    return

@login_required
@role_required("ADM")
@auth_bp.route("/register")
def register():
    return
    
