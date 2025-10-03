# /src/views/admin_routes.py
from flask import Blueprint, render_template, abort, flash, redirect, url_for, request
from flask_login import login_required, current_user
from src.utils.decorators.decorators import role_required
from src.models.Users import User, UserRole
from src.app import db  # seu SQLAlchemy
from src.views.forms import RegistrationForm, DeleteForm  # reaproveitando o form de registro

# Blueprint da área de administração
adm_bp = Blueprint("adm", __name__, url_prefix="/admin")


# -----------------------------
# LISTAGEM DE USUÁRIOS
# -----------------------------
@adm_bp.route('/db', methods=['GET'])
@login_required
@role_required('admin')
def admin_db_viewer():
    users = User.query.all()
    delete_form = DeleteForm()
    return render_template('admin_pages/db_viewer.html', users=users, delete_form=delete_form)


# -----------------------------
# EDIÇÃO DE USUÁRIO
# -----------------------------
@adm_bp.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = RegistrationForm(obj=user)

    if form.validate_on_submit():
        # Atualiza campos do usuário
        user.username = form.username.data
        user.role = UserRole(form.user_type.data)
        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash(f'Usuário {user.username} atualizado com sucesso!', 'success')
        return redirect(url_for('adm.admin_db_viewer'))

    return render_template('admin_pages/edit_user.html', form=form, user=user)


# -----------------------------
# EXCLUSÃO DE USUÁRIO
# -----------------------------
@adm_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    form = DeleteForm()
    if not form.validate_on_submit():
        abort(400)
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário {user.username} excluído com sucesso!', 'success')
    return redirect(url_for('adm.admin_db_viewer'))


# -----------------------------
# CRIAÇÃO DE NOVO USUÁRIO (opcional)
# -----------------------------
@adm_bp.route('/user/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        new_user = User(
            username=form.username.data,
            role=UserRole(form.user_type.data)
        )
        new_user.set_password(form.password.data)
        db.session.add(new_user)
        db.session.commit()
        flash(f'Usuário {new_user.username} criado com sucesso!', 'success')
        return redirect(url_for('adm.admin_db_viewer'))

    return render_template('admin_pages/edit_user.html', form=form, user=None)
