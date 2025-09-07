from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from materials.models import Course, Lesson
from users.models import User, Subscription


class LessonTestCase(APITestCase):

    def setUp(self):
        self.user = User.objects.create(email="testuser@mail.com")
        self.user.groups.clear()
        self.moderator_user = User.objects.create(email="moderator@mail.com")
        moderators_group = Group.objects.create(name="moderators")
        self.moderator_user.groups.add(moderators_group)

        self.course = Course.objects.create(name="Тестовый курс")
        self.lesson = Lesson.objects.create(
            name="Тестовый урок", course=self.course, owner=self.user
        )
        self.client.force_authenticate(user=self.user)

    def test_lesson_retrieve(self):
        """Проверка просмотра своего урока обычным пользователем"""
        url = reverse("materials:lesson_detail", args=(self.lesson.pk,))
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data.get("name"), self.lesson.name)

    def test_lesson_create(self):
        """Проверка создания своего урока обычным пользователем"""
        url = reverse("materials:lesson_create")
        data = {
            "name": "Тестовый урок номер 2",
            "video_link": "https://youtube.com/video.mp4",
            "course": self.course.pk,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.all().count(), 2)

    def test_lesson_update(self):
        """Проверка создания обновления своего урока обычным пользователем"""
        url = reverse("materials:lesson_update", args=(self.lesson.pk,))
        data = {"name": "Тестовый урок переименнованный"}
        response = self.client.patch(url, data)
        data_response = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(data_response.get("name"), "Тестовый урок переименнованный")

    def test_lesson_delete(self):
        """Проверка удаления своего урока обычным пользователем"""
        url = reverse("materials:lesson_destroy", args=(self.lesson.pk,))
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Lesson.objects.all().count(), 0)

    def test_lessons_list(self):
        """Проверка просмотра списка своих уроков обычным пользователем"""
        url = reverse("materials:lessons_list")
        response = self.client.get(url)
        result = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "id": self.lesson.pk,
                    "video_link": None,
                    "name": self.lesson.name,
                    "description": None,
                    "preview": None,
                    "course": self.course.pk,
                    "owner": self.user.pk,
                },
            ],
        }
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), result)

    def test_lesson_create_by_moderator_denied(self):
        """Проверка запрета создания урока модератором"""
        self.client.force_authenticate(user=self.moderator_user)
        url = reverse("materials:lesson_create")
        data = {
            "name": "Новый урок от модератора",
            "video_link": "https://youtube.com/new.mp4",
            "course": self.course.pk,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lesson_list_for_moderator(self):
        """Проверка получения полного списка уроков модератором"""
        self.client.force_authenticate(user=self.moderator_user)
        url = reverse("materials:lessons_list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
