from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
from app.models import Event, PhotoGroup, Photo, Order, OrderItem
from app import db
from flask_mail import Message
from app import mail
from flask import current_app

public_bp = Blueprint("public", __name__)


# =========================
# HOME (список событий)
# =========================
@public_bp.route("/")
def home():
    events = Event.query.filter_by(is_published=True).order_by(Event.id.desc()).all()
    return render_template("home.html", events=events)
public_bp.route("/")
def home():
    events = Event.query.filter_by(is_published=True).order_by(Event.id.desc()).all()
    return render_template("home.html", events=events)


# =========================
# EVENT DETAIL (список групп)
# =========================
@public_bp.route("/event/<int:event_id>")
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    return render_template("event_detail.html", event=event)


# =========================
# GROUP DETAIL (фото внутри группы)
# =========================
@public_bp.route("/group/<int:group_id>")
def group_detail(group_id):
    group = PhotoGroup.query.get_or_404(group_id)
    return render_template("group_detail.html", group=group)


# =========================
# ADD TO CART
# =========================
@public_bp.route("/add-to-cart/<int:photo_id>", methods=["POST"])
def add_to_cart(photo_id):
    cart = session.get("cart", [])

    if photo_id not in cart:
        cart.append(photo_id)

    session["cart"] = cart

    return redirect(request.referrer)


# =========================
# CART COUNT (для обновления счетчика)
# =========================
@public_bp.route("/cart-count")
def cart_count():
    cart = session.get("cart", [])
    return {'count': len(cart)}


# =========================
# CART
# =========================
@public_bp.route("/cart")
def cart():
    cart = session.get("cart", [])

    photos = Photo.query.filter(Photo.id.in_(cart)).all() if cart else []
    total = sum(photo.price for photo in photos)

    return render_template("cart.html", photos=photos, total=total)


# =========================
# REMOVE FROM CART
# =========================
@public_bp.route("/remove-from-cart/<int:photo_id>", methods=["POST"])
def remove_from_cart(photo_id):
    cart = session.get("cart", [])

    if photo_id in cart:
        cart.remove(photo_id)

    session["cart"] = cart

    return redirect(url_for("public.cart"))


# =========================
# CHECKOUT (только создание заказа, без отправки email)
# =========================
@public_bp.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart = session.get("cart", [])

    if not cart:
        return redirect(url_for("public.cart"))

    photos = Photo.query.filter(Photo.id.in_(cart)).all()
    total = sum(photo.price for photo in photos)

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")

        order = Order(
            customer_name=name,
            customer_phone=phone,
            customer_email=email,
            status="awaiting_payment"
        )

        db.session.add(order)
        db.session.flush()

        for photo in photos:
            item = OrderItem(
                order_id=order.id,
                photo_id=photo.id
            )
            db.session.add(item)

        db.session.commit()

        # Очищаем корзину
        session["cart"] = []

        # Перенаправляем на страницу оплаты (без отправки email)
        return redirect(url_for("public.payment_page", order_id=order.id))

    return render_template("checkout.html", photos=photos, total=total)


# =========================
# INFO
# =========================
@public_bp.route("/info")
def info():
    return render_template("info.html")


# =========================
# PAYMENT PAGE
# =========================
@public_bp.route("/payment/<int:order_id>")
def payment_page(order_id):
    order = Order.query.get_or_404(order_id)

    total = sum(item.photo.price for item in order.items)

    return render_template(
        "payment.html",
        order=order,
        total=total,
        qr_code="qr_sbp.jpg"  # или "qr_sbp.png" если есть
    )


# =========================
# CONFIRM PAYMENT (отправка email админу)
# =========================
@public_bp.route("/confirm-payment/<int:order_id>", methods=["POST"])
def confirm_payment(order_id):
    print(f"=== DEBUG: confirm_payment called for order {order_id} ===")

    order = Order.query.get_or_404(order_id)
    print(f"DEBUG: Order found - ID: {order.id}, Status: {order.status}")

    # Проверяем, что заказ ожидает оплаты
    if order.status != "awaiting_payment":
        print(f"DEBUG: Wrong status - {order.status}, redirecting to home")
        return redirect(url_for("public.home"))

    # Меняем статус на оплачен
    order.status = "paid"
    db.session.commit()
    print(f"DEBUG: Order {order.id} status changed to paid")

    # ===== ОТПРАВКА EMAIL АДМИНУ =====
    admin_link = url_for("admin.orders", _external=True)

    # Формируем список фотографий для письма
    photo_list = []
    for item in order.items:
        photo = item.photo
        group_name = photo.group.title if photo.group else "Без группы"
        photo_list.append(f"  • Фото #{photo.id} ({group_name}) - {photo.price} ₽")

    photo_list_text = "\n".join(photo_list) if photo_list else "  • Нет фотографий"

    total = sum(item.photo.price for item in order.items)

    msg = Message(
        subject=f"✅ Заказ №{order.id} ОПЛАЧЕН",
        recipients=[current_app.config["ADMIN_EMAIL"]]
    )

    msg.body = f"""
╔══════════════════════════════════════════════════════════╗
║                    ОПЛАЧЕН ЗАКАЗ №{order.id}                    ║
╚══════════════════════════════════════════════════════════╝

📋 ИНФОРМАЦИЯ О КЛИЕНТЕ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Имя:     {order.customer_name}
  Телефон: {order.customer_phone}
  Email:   {order.customer_email}

🖼 СОСТАВ ЗАКАЗА:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{photo_list_text}

💰 ИТОГО: {total} ₽
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 ССЫЛКА НА АДМИНКУ:
{admin_link}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else 'Дата не указана'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    # Отправляем письмо
    try:
        mail.send(msg)
        print(f"✅ Письмо об оплате заказа №{order.id} успешно отправлено!")
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")

    return render_template("success.html", order=order)


# =========================
# TEST PAYMENT (для отладки)
# =========================
@public_bp.route("/test-payment/<int:order_id>")
def test_payment(order_id):
    return f'''
    <h1>Test Payment for Order {order_id}</h1>
    <form method="POST" action="{url_for('public.confirm_payment', order_id=order_id)}">
        <button type="submit">Test Submit</button>
    </form>
    '''

@public_bp.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")

@public_bp.route("/public-offer")
def public_offer():
    return render_template("public_offer.html")