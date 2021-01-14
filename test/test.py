"""
Ran these test cases on a Mac
"""
from aws_s3_desktop_uploader import desktop_uploader as main
import unittest
import os
import pathlib
from datetime import datetime
from shutil import copyfile        

class Test(unittest.TestCase):

    def test_make_parallel_path(self):
        src_dir = "/apples/bananas"
        dst_dir = "/chair/table"
        src_path = "/apples/bananas/everything.jpg"
        self.assertEqual(main.make_parallel_path(src_dir, dst_dir, src_path, add_date_subdir=False),
            "/chair/table/everything.jpg"
        )

    def test_make_parallel_path_2(self):
        src_dir = "/Users/russelltran/Desktop/magic_uploader/unprocessed"
        dst_dir = "/Users/russelltran/Desktop/magic_uploader/done"
        src_path = "/Users/russelltran/Desktop/magic_uploader/unprocessed/watermelon.jpg"
        self.assertEqual(main.make_parallel_path(src_dir, dst_dir, src_path, add_date_subdir=False),
            "/Users/russelltran/Desktop/magic_uploader/done/watermelon.jpg"
    )

    def test_make_parallel_path_3(self):
        src_dir = "/Users/russelltran/Desktop/magic_uploader/unprocessed"
        dst_dir = "/Users/russelltran/Desktop/magic_uploader/done"
        src_path = "/Users/russelltran/Desktop/magic_uploader/unprocessed/watermelon.jpg"
        self.assertEqual(main.make_parallel_path(src_dir, dst_dir, src_path),
            "/Users/russelltran/Desktop/magic_uploader/done/{}/watermelon.jpg".format(
                datetime.today().strftime('%Y-%m-%d')
            )
        )

    def test_make_parallel_path_4(self):
        src_dir = "/Users/russelltran/Desktop/magic_uploader/unprocessed"
        dst_dir = "/Users/russelltran/Desktop/magic_uploader/done"
        src_path = "/Users/russelltran/Desktop/magic_uploader/unprocessed/trout/computer/watermelon.jpg"
        self.assertEqual(main.make_parallel_path(src_dir, dst_dir, src_path),
            "/Users/russelltran/Desktop/magic_uploader/done/{}/trout/computer/watermelon.jpg".format(
                datetime.today().strftime('%Y-%m-%d')
            )
        )

    def test_creation_date(self):
        path = "/tmp/HappyFace.jpg"
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "HappyFace.jpg"), path)
        # print("test_creation_date")
        # print(main.creation_date(path))

    def test_get_file_created(self):
        path = "/tmp/HappyFace.jpg"
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "HappyFace.jpg"), path)
        # print("test_get_file_created")
        # print(main.get_file_created(path))

    def test_get_metadata(self):
        path = "/tmp/HappyFace.jpg"
        copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "HappyFace.jpg"), path)
        # print("test_get_metadata")
        # print(main.get_metadata(path))

    def test_generate_bucket_key(self):
        for i in range(10):
            self.assertRegex(
                main.generate_bucket_key("/Users/russell/Documents/taco_tuesday.jpg", "images/raw/"),
                "images/raw/taco_tuesday-[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}.jpg"
            )

    def test_move(self):
        pass
        # copyfile(os.path.join(pathlib.Path(__file__).parent.absolute(), "HappyFace.jpg"), "/tmp/HappyFace.jpg")
        # assert os.path.isfile("/tmp/HappyFace.jpg")
        # main.move("/tmp/HappyFace.jpg", "/tmp")
        # self.assertEqual(os.path.isfile("/tmp/{}/HappyFace.jpg".format(datetime.today().strftime('%Y-%m-%d'))), True)
        
if __name__ == '__main__':
    unittest.main()