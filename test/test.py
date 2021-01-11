"""
Ran these test cases on a Mac
"""
import main
import unittest
import os
import pathlib
from datetime import datetime
from shutil import copyfile        

class Test(unittest.TestCase):

    def test_creation_date(self):
        path = "/tmp/HappyFace.jpg"
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "test/HappyFace.jpg"), path)
        print("test_creation_date")
        print(main.creation_date(path))

    def test_get_file_created(self):
        path = "/tmp/HappyFace.jpg"
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "test/HappyFace.jpg"), path)
        print("test_get_file_created")
        print(main.get_file_created(path))

    def test_get_metadata(self):
        path = "/tmp/HappyFace.jpg"
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "test/HappyFace.jpg"), path)
        print("test_get_metadata")
        print(main.get_metadata(path))

    def test_generate_bucket_key(self):
        for i in range(10):
            self.assertRegex(
                main.generate_bucket_key("/Users/russell/Documents/taco_tuesday.jpg", "images/raw/"),
                "images/raw/taco_tuesday-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}.jpg"
            )

    def test_move(self):
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "test/HappyFace.jpg"), "/tmp/HappyFace.jpg")
        assert os.path.isfile("/tmp/HappyFace.jpg")
        main.move("/tmp/HappyFace.jpg", "/tmp")
        self.assertEqual(os.path.isfile("/tmp/{}/HappyFace.jpg".format(datetime.today().strftime('%Y-%m-%d'))), True)

    

        
if __name__ == '__main__':
    unittest.main()