from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from flask_login import login_user, logout_user, login_required
from app.models import Order, Event, Photo, Admin, PhotoGroup
from app import db
from werkzeug.utils import secure_filename
import os
import time
from app.utils.image_utils import create_watermarked_image

admin_bp = Blueprint('admin', __name__)


# ------------------------
# LOGIN
# ------------------------

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        admin = Admin.query.filter_by(username=username).first()

        if admin and admin.check_password(password):
            login_user(admin)
            return redirect(url_for("admin.dashboard"))

        return render_template("admin/login.html", error="Неверный логин или пароль")

    return render_template("admin/login.html")


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))


# ------------------------
# DASHBOARD (CREATE AND LIST EVENTS)
# ------------------------

@admin_bp.route('/', methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")

        file = request.files.get("preview_image")
        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)

            upload_folder = current_app.config["UPLOAD_FOLDER"]

            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            file.save(os.path.join(upload_folder, filename))

        event = Event(
            title=title,
            description=description,
            preview_image=filename
        )

        db.session.add(event)
        db.session.commit()

        flash("Событие успешно создано")
        return redirect(url_for("admin.dashboard"))

    events = Event.query.order_by(Event.id.desc()).all()
    return render_template('admin/admin_events.html', events=events)


# ------------------------
# TOGGLE EVENT PUBLISH STATUS
# ------------------------

@admin_bp.route('/toggle-event/<int:event_id>')
@login_required
def toggle_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.is_published = not event.is_published
    db.session.commit()
    flash(f"Статус события изменен на {'опубликовано' if event.is_published else 'не опубликовано'}")
    return redirect(url_for('admin.dashboard'))


# ------------------------
# DELETE EVENT
# ------------------------

@admin_bp.route("/delete-event/<int:event_id>", methods=["POST"])
@login_required
def delete_event(event_id):
    event = Event.query.get_or_404(event_id)

    # Удаляем связанные фотографии и группы
    for group in event.groups:
        for photo in group.photos:
            for filename in [
                photo.preview_filename,
                photo.thumb_filename
            ]:
                if filename:
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            db.session.delete(photo)
        db.session.delete(group)

    # Удаляем превью события
    if event.preview_image:
        preview_path = os.path.join(current_app.config['UPLOAD_FOLDER'], event.preview_image)
        if os.path.exists(preview_path):
            os.remove(preview_path)

    db.session.delete(event)
    db.session.commit()

    flash("Событие удалено")
    return redirect(url_for("admin.dashboard"))


# ------------------------
# MANAGE GROUPS
# ------------------------

@admin_bp.route("/event/<int:event_id>/groups")
@login_required
def manage_groups(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template("admin/manage_groups.html", event=event)


@admin_bp.route("/event/<int:event_id>/groups/create", methods=["POST"])
@login_required
def create_group(event_id):
    event = Event.query.get_or_404(event_id)
    title = request.form.get("title")

    if title:
        group = PhotoGroup(title=title, event_id=event.id)
        db.session.add(group)
        db.session.commit()
        flash("Группа создана")

    return redirect(url_for("admin.manage_groups", event_id=event.id))


@admin_bp.route("/group/<int:group_id>/delete", methods=["POST"])
@login_required
def delete_group(group_id):
    group = PhotoGroup.query.get_or_404(group_id)
    event_id = group.event_id

    # Удаляем фотографии группы
    for photo in group.photos:
        for filename in [
            photo.preview_filename,
            photo.thumb_filename
        ]:
            if filename:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
        db.session.delete(photo)

    db.session.delete(group)
    db.session.commit()

    flash("Группа удалена")
    return redirect(url_for("admin.manage_groups", event_id=event_id))


# ------------------------
# UPLOAD PHOTO TO GROUP
# ------------------------

@admin_bp.route('/group/<int:group_id>/upload-photo', methods=['POST'])
@login_required
def upload_photo(group_id):
    group = PhotoGroup.query.get_or_404(group_id)

    file = request.files.get('photo')
    price = request.form.get('price')

    if not file or not price:
        flash("Не выбрано фото или не указана цена")
        return redirect(url_for('admin.manage_groups', event_id=group.event_id))

    try:
        price = float(price)
    except ValueError:
        flash("Некорректная цена")
        return redirect(url_for('admin.manage_groups', event_id=group.event_id))

    filename = secure_filename(file.filename)
    upload_folder = current_app.config['UPLOAD_FOLDER']

    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    timestamp = int(time.time())

    temp_path = os.path.join(upload_folder, f"temp_{timestamp}_{filename}")
    file.save(temp_path)

    # PREVIEW (большая версия с водяным знаком)
    preview_filename = f"preview_{timestamp}_{filename}"
    preview_path = os.path.join(upload_folder, preview_filename)

    create_watermarked_image(
        temp_path,
        preview_path,
        max_size=(1400, 1400)
    )

    # THUMBNAIL (маленькая версия с водяным знаком)
    thumb_filename = f"thumb_{timestamp}_{filename}"
    thumb_path = os.path.join(upload_folder, thumb_filename)

    create_watermarked_image(
        temp_path,
        thumb_path,
        max_size=(400, 400)
    )

    # Удаляем временный оригинал
    if os.path.exists(temp_path):
        os.remove(temp_path)

    new_photo = Photo(
        preview_filename=preview_filename,
        thumb_filename=thumb_filename,
        price=price,
        group_id=group.id
    )

    db.session.add(new_photo)
    db.session.commit()

    flash("Фото загружено и обработано")
    return redirect(url_for('admin.manage_groups', event_id=group.event_id))


# ------------------------
# DELETE PHOTO
# ------------------------

@admin_bp.route('/photo/<int:photo_id>/delete', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    group = photo.group

    for filename in [
        photo.preview_filename,
        photo.thumb_filename
    ]:
        if filename:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)

    db.session.delete(photo)
    db.session.commit()

    flash("Фото удалено")
    return redirect(url_for('admin.manage_groups', event_id=group.event_id))


# ------------------------
# ORDERS MANAGEMENT
# ------------------------

@admin_bp.route("/orders")
@login_required
def orders():
    orders = Order.query.order_by(Order.id.desc()).all()
    return render_template("admin/orders.html", orders=orders)


@admin_bp.route("/orders/<int:order_id>/confirm", methods=["POST"])
@login_required
def confirm_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "confirmed"
    db.session.commit()
    flash("Заказ подтвержден")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = "cancelled"
    db.session.commit()
    flash("Заказ отменен")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/orders/<int:order_id>/delete", methods=["POST"])
@login_required
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash("Заказ удален")
    return redirect(url_for("admin.orders"))