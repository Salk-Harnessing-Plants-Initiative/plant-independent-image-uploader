"""
Ran these test cases on a Mac
"""
import script
import unittest
import os
import pathlib
from datetime import datetime
from shutil import copyfile

class Test(unittest.TestCase):

    def test_generate_bucket_key(self):
        for i in range(10):
            self.assertRegex(
                script.generate_bucket_key("/Users/russell/Documents/taco_tuesday.jpg"),
                "taco_tuesday-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}.jpg"
            )

    def test_move(self):
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "test/HappyFace.jpg"), "/tmp/HappyFace.jpg")
        assert os.path.isfile("/tmp/HappyFace.jpg")
        script.move("/tmp/HappyFace.jpg", "/tmp")
        self.assertEqual(os.path.isfile("/tmp/{}/HappyFace.jpg".format(datetime.today().strftime('%Y-%m-%d'))), True)
        
if __name__ == '__main__':
    unittest.main()