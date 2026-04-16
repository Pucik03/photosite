from PIL import Image, ImageDraw, ImageFont


def create_watermarked_image(input_path, output_path, max_size):
    """
    Создает изображение строго указанного размера с водяным знаком
    """
    with Image.open(input_path) as img:
        # Конвертируем в RGBA для работы с прозрачностью
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Определяем целевые размеры
        if isinstance(max_size, tuple):
            target_width, target_height = max_size
        else:
            target_width = target_height = max_size

        # Обрезка до нужных пропорций
        img_width, img_height = img.size
        target_ratio = target_width / target_height
        img_ratio = img_width / img_height

        if img_ratio > target_ratio:
            new_width = int(img_height * target_ratio)
            offset = (img_width - new_width) // 2
            img = img.crop((offset, 0, offset + new_width, img_height))
        else:
            new_height = int(img_width / target_ratio)
            offset = (img_height - new_height) // 2
            img = img.crop((0, offset, img_width, offset + new_height))

        # Изменяем размер
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Создаем слой для водяного знака
        watermark = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)

        # Настройки водяного знака
        watermark_text = "© Фотомагазин"
        font_size = max(int(min(target_width, target_height) / 18), 12)

        # Загрузка шрифта
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()

        # Получаем размеры текста
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Позиция
        x = target_width - text_width - 15
        y = target_height - text_height - 15

        # Рисуем полупрозрачную подложку
        padding = 5
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 180)  # Черный с прозрачностью
        )

        # Рисуем текст
        draw.text((x, y), watermark_text, fill=(255, 255, 255, 255), font=font)

        # Объединяем изображение с водяным знаком
        img = Image.alpha_composite(img, watermark)

        # Конвертируем обратно в RGB для сохранения как JPEG
        img = img.convert('RGB')

        # Сохраняем
        img.save(output_path, quality=90, optimize=True)