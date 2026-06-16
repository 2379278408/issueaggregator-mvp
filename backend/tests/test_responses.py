import unittest

from app.responses import error_response, success_response


class SuccessResponseTests(unittest.TestCase):
    def test_data_dict(self) -> None:
        result = success_response({'items': [], 'total': 0})
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], {'items': [], 'total': 0})

    def test_data_none(self) -> None:
        result = success_response(None)
        self.assertTrue(result['success'])
        self.assertIsNone(result['data'])

    def test_data_string(self) -> None:
        result = success_response('ok')
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], 'ok')

    def test_data_list(self) -> None:
        result = success_response([1, 2, 3])
        self.assertTrue(result['success'])
        self.assertEqual(result['data'], [1, 2, 3])


class ErrorResponseTests(unittest.TestCase):
    def test_struct_keys(self) -> None:
        result = error_response('NOT_FOUND', 'Not found')
        self.assertFalse(result['success'])
        self.assertEqual(result['error_code'], 'NOT_FOUND')
        self.assertEqual(result['message'], 'Not found')

    def test_empty_message(self) -> None:
        result = error_response('UNKNOWN', '')
        self.assertEqual(result['error_code'], 'UNKNOWN')
        self.assertEqual(result['message'], '')

    def test_uppercase_code(self) -> None:
        result = error_response('VALIDATION_ERROR', 'invalid input')
        self.assertEqual(result['error_code'], 'VALIDATION_ERROR')
