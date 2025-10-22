from flask import Blueprint, render_template, request, redirect, jsonify, session
from app.extensions import db
from app.models import Sale, SaleItem, Part
from app.utils.security import admin_required
from app.utils.file_handling import delete_part_folder, delete_image_file, delete_video_file
from datetime import datetime
import math

sales_bp = Blueprint('sales', __name__)


@sales_bp.route("/sales", methods=["GET"])
@admin_required
def sales_list():
    sales = Sale.query.order_by(Sale.created_at.desc()).all()
    return render_template("sales_list.html", sales=sales)


@sales_bp.route("/sales/new", methods=["GET"])
@admin_required
def new_sale():
    parts = Part.query.filter(Part.quantity > 0).all()
    return render_template("new_sale.html", parts=parts)


@sales_bp.route("/sales/new", methods=["POST"])
@admin_required
def create_sale():
    try:
        # Получаем данные из формы
        discount_type = request.form.get('discount_type')
        discount_value = int(request.form.get('discount_value', 0))
        transport_company = request.form.get('transport_company', '')
        tracking_number = request.form.get('tracking_number', '')

        # Получаем товары из формы
        part_ids = request.form.getlist('part_id[]')
        quantities = request.form.getlist('quantity[]')

        if not part_ids:
            return "Не выбраны товары для продажи", 400

        # Создаем продажу
        sale = Sale(
            discount_type=discount_type,
            discount_value=discount_value,
            transport_company=transport_company,
            tracking_number=tracking_number
        )

        db.session.add(sale)
        db.session.flush()

        # Добавляем товары в продажу и обновляем остатки
        total_amount = 0
        parts_to_delete = []

        for i, part_id in enumerate(part_ids):
            part = Part.query.get(int(part_id))
            quantity = int(quantities[i])

            if part and quantity > 0:
                if quantity > part.quantity:
                    return f"Недостаточно товара: {part.name}. В наличии: {part.quantity}", 400

                item_total = part.price_out * quantity
                total_amount += item_total

                # Создаем запись о продаже с сохранением данных о детали
                sale_item = SaleItem(
                    sale_id=sale.id,
                    part_id=part.id,
                    quantity=quantity,
                    unit_price=part.price_out,
                    total_price=item_total,
                    part_name=part.name,  # Сохраняем название
                    part_car=part.car,  # Сохраняем авто
                    part_number=part.part_number  # Сохраняем артикул
                )
                db.session.add(sale_item)

                # Обновляем количество на складе
                part.quantity -= quantity

                # Если товар закончился, помечаем для удаления
                if part.quantity == 0:
                    parts_to_delete.append(part)

        # Рассчитываем скидку
        if discount_type == 'percent' and discount_value > 0:
            discount_amount = math.ceil(total_amount * (discount_value / 100))
        elif discount_type == 'fixed' and discount_value > 0:
            discount_amount = discount_value
        else:
            discount_amount = 0

        final_amount = total_amount - discount_amount

        sale.total_amount = total_amount
        sale.final_amount = final_amount

        db.session.commit()

        # Удаляем детали, которые закончились (файлы и записи из parts)
        for part in parts_to_delete:
            delete_part_completely(part.id)

        return redirect('/sales')

    except Exception as e:
        db.session.rollback()
        return f"Ошибка при создании продажи: {str(e)}", 400


def delete_part_completely(part_id):
    """Полностью удаляет деталь со всеми файлами, но данные остаются в продажах"""
    try:
        part = Part.query.get(part_id)
        if not part:
            return

        # Удаляем файлы изображений с диска
        for image in part.images:
            delete_image_file(part.id, image.filename)

        # Удаляем файлы видео с диска
        for video in part.videos:
            delete_video_file(part.id, video.filename)

        # Удаляем папку детали полностью
        delete_part_folder(part.id)

        # Удаляем деталь из БД (данные остаются в sale_items через part_name, part_car, part_number)
        db.session.delete(part)
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Ошибка при удалении детали: {e}")


@sales_bp.route("/sales/<int:sale_id>", methods=["GET"])
@admin_required
def sale_detail(sale_id):
    sale = Sale.query.get_or_404(sale_id)
    return render_template("sale_detail.html", sale=sale)


@sales_bp.route("/api/parts/search", methods=["GET"])
@admin_required
def search_parts():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])

    parts = Part.query.filter(
        db.or_(
            Part.name.ilike(f'%{query}%'),
            Part.part_number.ilike(f'%{query}%'),
            Part.car.ilike(f'%{query}%')
        ),
        Part.quantity > 0
    ).limit(10).all()

    result = []
    for part in parts:
        result.append({
            'id': part.id,
            'name': part.name,
            'part_number': part.part_number,
            'car': part.car,
            'price_out': part.price_out,
            'quantity': part.quantity,
            'stock_info': f"{part.name} | {part.car} | {part.part_number} | {part.price_out} руб. | В наличии: {part.quantity} шт."
        })

    return jsonify(result)