import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi import HTTPException
from backend import main


class AdminSafetyTests(unittest.TestCase):
    def test_admin_profile_deletion_never_opens_database(self):
        with patch.object(main, 'db') as database:
            with self.assertRaises(HTTPException) as caught:
                main.delete_own_profile({'role': 'admin', 'sub': 'admin-id'})
            self.assertEqual(caught.exception.status_code, 403)
            database.assert_not_called()

    def test_missing_admin_password_never_seeds(self):
        with patch.object(main, 'ADMIN_PASSWORD', ''), patch.object(main, 'db') as database:
            with self.assertRaises(RuntimeError):
                main.seed_database()
            database.assert_not_called()

    def test_moderation_cannot_delete_an_admin(self):
        with patch.object(main, 'db') as database, patch.object(main, 'delete_user_account') as delete:
            cursor = database.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
            cursor.fetchone.return_value = {'role': 'admin'}
            with self.assertRaises(HTTPException) as caught:
                main.admin_user_status('admin-id', main.StatusIn(status='deleted'), {'sub': 'actor-id'})
            self.assertEqual(caught.exception.status_code, 400)
            delete.assert_not_called()

    def test_web_route_cannot_read_files_outside_build(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            build=root/'web-build'
            build.mkdir()
            (root/'private.env').write_text('private configuration',encoding='utf-8')
            with patch.object(main, 'WEB_BUILD', build):
                with self.assertRaises(HTTPException) as caught:
                    main.react_web('../private.env')
                self.assertEqual(caught.exception.status_code, 404)


if __name__ == '__main__':
    unittest.main()
