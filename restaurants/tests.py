# restaurants/tests.py
from django.test import TestCase
from restaurants.models import Restaurant, Tag, OpeningHour
from restaurants.utils import apply_intelligent_tags
import datetime

class TaggingSystemTestCase(TestCase):
    def setUp(self):
        self.restaurant = Restaurant.objects.create(
            name="Test Mamak",
            cuisine="Mamak, Japanese, cheap_food",
            latitude=3.1390,
            longitude=101.6869
        )
        OpeningHour.objects.create(
            restaurant=self.restaurant,
            day=0,
            opening_time=datetime.time(8, 0),
            closing_time=datetime.time(15, 0)
        )

    def test_intelligent_tagging(self):
        apply_intelligent_tags(self.restaurant)

        # 获取该餐厅关联的所有标签名称
        tag_names = list(self.restaurant.tags.values_list('name', flat=True))

        # 1. 验证时间与同义词推导
        self.assertIn('Breakfast', tag_names)
        self.assertIn('Lunch', tag_names)
        self.assertIn('Halal', tag_names)
        self.assertIn('Japanese', tag_names)

        # 2. 验证下划线替换与未知词降级隔离（cheap_food -> 'Cheap Food'）
        cheap_tag = Tag.objects.get(name='Cheap Food')
        self.assertEqual(cheap_tag.tag_type, 'other')