import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image as PILImage
from rest_framework.test import APITestCase

from .models import Annotation, Image
from .serializers import MAX_UPLOAD_BYTES

User = get_user_model()

VALID_POINTS = [[0.1, 0.1], [0.5, 0.2], [0.9, 0.9]]


def make_upload(name="scan.png", image_format="PNG", size=(48, 32), extra_bytes=0):
    buffer = io.BytesIO()
    PILImage.new("RGB", size, (18, 27, 38)).save(buffer, format=image_format)
    # Trailing padding keeps the file a decodable image while inflating its size.
    data = buffer.getvalue() + b"\0" * extra_bytes
    return SimpleUploadedFile(name, data, content_type=f"image/{image_format.lower()}")


class MediaAPITestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.temp_media = tempfile.mkdtemp(prefix="taskcanvas-test-media-")
        cls.media_override = override_settings(MEDIA_ROOT=cls.temp_media)
        cls.media_override.enable()
        cls.addClassCleanup(cls.media_override.disable)
        cls.addClassCleanup(shutil.rmtree, cls.temp_media, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user("a@example.com", "pass-12345")
        self.other = User.objects.create_user("b@example.com", "pass-12345")
        self.client.force_authenticate(self.user)

    def make_image(self, user=None):
        return Image.objects.create(
            user=user or self.user,
            file=make_upload(),
            original_name="scan.png",
            width=48,
            height=32,
        )


class ImageAPITests(MediaAPITestCase):
    def test_upload_stores_dimensions_and_name(self):
        response = self.client.post(
            "/api/images/", {"file": make_upload()}, format="multipart"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["original_name"], "scan.png")
        self.assertEqual(response.data["width"], 48)
        self.assertEqual(response.data["height"], 32)
        self.assertEqual(response.data["annotation_count"], 0)

    def test_upload_rejects_oversize_file(self):
        big = make_upload(extra_bytes=MAX_UPLOAD_BYTES)
        response = self.client.post("/api/images/", {"file": big}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data["errors"])

    def test_upload_rejects_unsupported_format(self):
        gif = make_upload(name="anim.gif", image_format="GIF")
        response = self.client.post("/api/images/", {"file": gif}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data["errors"])

    def test_upload_rejects_non_image(self):
        junk = SimpleUploadedFile("notes.txt", b"hello world", content_type="text/plain")
        response = self.client.post("/api/images/", {"file": junk}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_list_is_user_scoped_and_counts_annotations(self):
        mine = self.make_image()
        Annotation.objects.create(image=mine, points=VALID_POINTS)
        Annotation.objects.create(image=mine, points=VALID_POINTS)
        self.make_image(user=self.other)
        response = self.client.get("/api/images/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["annotation_count"], 2)

    def test_delete_removes_annotations(self):
        image = self.make_image()
        Annotation.objects.create(image=image, points=VALID_POINTS)
        response = self.client.delete(f"/api/images/{image.pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Annotation.objects.count(), 0)

    def test_cannot_touch_other_users_image(self):
        theirs = self.make_image(user=self.other)
        self.assertEqual(self.client.get(f"/api/images/{theirs.pk}/").status_code, 404)
        self.assertEqual(self.client.delete(f"/api/images/{theirs.pk}/").status_code, 404)


class AnnotationAPITests(MediaAPITestCase):
    def annotate(self, image, **overrides):
        payload = {"points": VALID_POINTS, "color": "#ff0000", "label": "nodule"}
        payload.update(overrides)
        return self.client.post(
            f"/api/images/{image.pk}/annotations/", payload, format="json"
        )

    def test_create_and_list_annotations(self):
        image = self.make_image()
        response = self.annotate(image)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["points"], VALID_POINTS)
        listing = self.client.get(f"/api/images/{image.pk}/annotations/")
        self.assertEqual(len(listing.data), 1)

    def test_polygon_needs_three_vertices(self):
        response = self.annotate(self.make_image(), points=[[0.1, 0.1], [0.5, 0.5]])
        self.assertEqual(response.status_code, 400)
        self.assertIn("points", response.data["errors"])

    def test_coordinates_must_be_normalized(self):
        response = self.annotate(self.make_image(), points=[[0.1, 0.1], [2, 0.5], [1, 1]])
        self.assertEqual(response.status_code, 400)

    def test_vertices_must_be_pairs(self):
        response = self.annotate(self.make_image(), points=[[0.1, 0.1], [0.5], [1, 1]])
        self.assertEqual(response.status_code, 400)

    def test_color_must_be_hex(self):
        response = self.annotate(self.make_image(), color="red")
        self.assertEqual(response.status_code, 400)

    def test_create_defaults_to_polygon(self):
        response = self.annotate(self.make_image())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["shape_type"], "polygon")

    def test_create_rectangle_point_and_polyline(self):
        image = self.make_image()
        cases = [
            ("rectangle", [[0.1, 0.1], [0.6, 0.5]]),
            ("point", [[0.5, 0.5]]),
            ("polyline", [[0.1, 0.9], [0.5, 0.2], [0.9, 0.8]]),
        ]
        for shape_type, points in cases:
            response = self.annotate(image, shape_type=shape_type, points=points)
            self.assertEqual(response.status_code, 201, msg=shape_type)
            self.assertEqual(response.data["shape_type"], shape_type)
            self.assertEqual(response.data["points"], points)

    def test_shape_point_count_rules_enforced(self):
        image = self.make_image()
        bad_cases = [
            ("rectangle", [[0.1, 0.1], [0.4, 0.4], [0.6, 0.6]]),  # exactly 2 required
            ("point", [[0.1, 0.1], [0.2, 0.2]]),  # exactly 1 required
            ("polyline", [[0.5, 0.5]]),  # at least 2 required
            ("polygon", [[0.1, 0.1], [0.5, 0.5]]),  # at least 3 required
        ]
        for shape_type, points in bad_cases:
            response = self.annotate(image, shape_type=shape_type, points=points)
            self.assertEqual(response.status_code, 400, msg=shape_type)
            self.assertIn("points", response.data["errors"])

    def test_invalid_shape_type_rejected(self):
        response = self.annotate(self.make_image(), shape_type="circle")
        self.assertEqual(response.status_code, 400)

    def test_update_respects_existing_shape_rules(self):
        image = self.make_image()
        rect_id = self.annotate(
            image, shape_type="rectangle", points=[[0.1, 0.1], [0.5, 0.5]]
        ).data["id"]
        response = self.client.patch(
            f"/api/annotations/{rect_id}/",
            {"points": [[0.1, 0.1], [0.4, 0.4], [0.6, 0.6]]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_annotation_points_label_and_color(self):
        image = self.make_image()
        annotation_id = self.annotate(image).data["id"]
        new_points = [[0.2, 0.2], [0.8, 0.25], [0.75, 0.8], [0.25, 0.75]]
        response = self.client.patch(
            f"/api/annotations/{annotation_id}/",
            {"points": new_points, "label": "reshaped", "color": "#34d399"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["points"], new_points)
        self.assertEqual(response.data["label"], "reshaped")
        self.assertEqual(response.data["color"], "#34d399")

    def test_update_rejects_invalid_points(self):
        image = self.make_image()
        annotation_id = self.annotate(image).data["id"]
        response = self.client.patch(
            f"/api/annotations/{annotation_id}/",
            {"points": [[0.2, 0.2], [1.5, 0.5], [0.5, 0.9]]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("points", response.data["errors"])

    def test_cannot_update_other_users_annotation(self):
        theirs = Annotation.objects.create(
            image=self.make_image(user=self.other), points=VALID_POINTS
        )
        response = self.client.patch(
            f"/api/annotations/{theirs.pk}/", {"label": "hijacked"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_annotation(self):
        image = self.make_image()
        annotation_id = self.annotate(image).data["id"]
        response = self.client.delete(f"/api/annotations/{annotation_id}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Annotation.objects.count(), 0)

    def test_cannot_annotate_other_users_image(self):
        theirs = self.make_image(user=self.other)
        self.assertEqual(self.annotate(theirs).status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/images/{theirs.pk}/annotations/").status_code, 404
        )

    def test_cannot_delete_other_users_annotation(self):
        theirs = Annotation.objects.create(
            image=self.make_image(user=self.other), points=VALID_POINTS
        )
        self.assertEqual(self.client.delete(f"/api/annotations/{theirs.pk}/").status_code, 404)
