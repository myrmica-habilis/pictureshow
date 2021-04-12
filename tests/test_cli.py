from pathlib import Path
import subprocess

from PyPDF2 import PdfFileReader
import pytest

PIC_FILE = 'pics/mandelbrot.png'
PICS_1_GOOD = (PIC_FILE,)
PICS_2_GOOD = (PIC_FILE, 'pics/blender/chain_render.jpg')
PICS_1_GLOB = ('pics/plots/gauss*',)
PICS_2_GLOBS = ('pics/blender/*.png', 'pics/m*')
PICS_2_GOOD_1_BAD = (PIC_FILE, 'pics/empty.pdf', 'pics/mandelbrot.jpg')
PICS_2_BAD_1_GOOD = ('pics/not_jpg.jpg', PIC_FILE, 'pics/empty.pdf')
PICS_1_BAD = ('pics/not_jpg.jpg',)
PICS_2_BAD = ('pics/not_jpg.jpg', 'pics/empty.pdf')
PICS_DIR = ('pics',)
PICS_MISSING = ('missing.png',)


@pytest.fixture(params=['pictureshow', 'python -m pictureshow'])
def app_exec(request):
    """Executable to run in CLI tests."""
    return request.param


@pytest.fixture(scope='function')
def temp_pdf():
    pdf_path = Path('_test_temp_.pdf')
    yield pdf_path

    # teardown
    if pdf_path.exists():
        pdf_path.unlink()


class TestCallsToCore:
    """Test that the command line app calls the underlying function
    correctly.
    """
    pass


class TestOutput:
    """Test stdout/stderr and return code of the command line app."""
    pass

    @pytest.mark.parametrize(
        'pic_files, num_pics',
        (
            pytest.param(PICS_1_GOOD, '1 picture', id='1 good'),
            pytest.param(PICS_2_GOOD, '2 pictures', id='2 good'),
            pytest.param(PICS_1_GLOB, '2 pictures', id='glob'),
            pytest.param(PICS_2_GLOBS, '4 pictures', id='2 globs'),
        )
    )
    def test_valid_input(self, app_exec, temp_pdf, pic_files, num_pics):
        command = f'{app_exec} {" ".join(pic_files)} {temp_pdf}'
        proc = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        std_out = proc.stdout.decode()

        assert proc.returncode == 0
        assert f'Saved {num_pics} to ' in std_out
        assert 'skipped' not in std_out
        assert 'Nothing' not in std_out

    @pytest.mark.parametrize(
        'pic_files, num_valid, num_invalid',
        (
            pytest.param(PICS_2_GOOD_1_BAD, '2 pictures', '1 file',
                         id='2 good, 1 bad'),
            pytest.param(PICS_2_BAD_1_GOOD, '1 picture', '2 files',
                         id='2 bad, 1 good'),
        )
    )
    def test_valid_and_invalid_input(self, app_exec, temp_pdf, pic_files,
                                     num_valid, num_invalid):
        command = f'{app_exec} {" ".join(pic_files)} {temp_pdf}'
        proc = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        std_out = proc.stdout.decode()

        assert proc.returncode == 0
        assert f'{num_invalid} skipped due to error.' in std_out
        assert f'Saved {num_valid} to ' in std_out
        assert 'Nothing' not in std_out

    @pytest.mark.parametrize(
        'pic_files, num_invalid',
        (
            pytest.param(PICS_1_BAD, '1 file', id='1bad'),
            pytest.param(PICS_2_BAD, '2 files', id='2bad'),
            pytest.param(PICS_DIR, '1 file', id='dir'),
            pytest.param(PICS_MISSING, '1 file', id='missing'),
        )
    )
    def test_invalid_input(self, app_exec, temp_pdf, pic_files, num_invalid):
        command = f'{app_exec} {" ".join(pic_files)} {temp_pdf}'
        proc = subprocess.run(command, shell=True, stdout=subprocess.PIPE)
        std_out = proc.stdout.decode()

        assert proc.returncode == 0
        assert f'{num_invalid} skipped due to error.' in std_out
        assert 'Saved' not in std_out
        assert 'Nothing to save.' in std_out


def assert_pdf(path, num_pages):
    assert path.exists()
    assert path.stat().st_size > 0
    assert PdfFileReader(str(path)).numPages == num_pages


class TestGeneratedFile:
    """Test the PDF file generated by the command line app."""

    @pytest.mark.parametrize(
        'pic_files, num_pics',
        (
            pytest.param(PICS_1_GOOD, 1, id='1 good'),
            pytest.param(PICS_2_GOOD, 2, id='2 good'),
            pytest.param(PICS_1_GLOB, 2, id='glob'),
            pytest.param(PICS_2_GLOBS, 4, id='2 globs'),
        )
    )
    def test_valid_input(self, app_exec, temp_pdf, pic_files, num_pics):
        command = f'{app_exec} {" ".join(pic_files)} {temp_pdf}'
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)

        assert_pdf(temp_pdf, num_pages=num_pics)

    @pytest.mark.parametrize(
        'pic_files, num_valid',
        (
            pytest.param(PICS_2_GOOD_1_BAD, 2, id='2 good, 1 bad'),
            pytest.param(PICS_2_BAD_1_GOOD, 1, id='2 bad, 1 good'),
        )
    )
    def test_valid_and_invalid_input(self, app_exec, temp_pdf, pic_files,
                                     num_valid):
        command = f'{app_exec} {" ".join(pic_files)} {temp_pdf}'
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)

        assert_pdf(temp_pdf, num_pages=num_valid)

    @pytest.mark.parametrize(
        'pic_files',
        (
            pytest.param(PICS_1_BAD, id='1bad'),
            pytest.param(PICS_2_BAD, id='2bad'),
            pytest.param(PICS_DIR, id='dir'),
            pytest.param(PICS_MISSING, id='missing'),
        )
    )
    def test_invalid_input(self, app_exec, temp_pdf, pic_files):
        command = f'{app_exec} {" ".join(pic_files)} {temp_pdf}'
        subprocess.run(command, shell=True, stdout=subprocess.PIPE)

        assert not temp_pdf.exists()
