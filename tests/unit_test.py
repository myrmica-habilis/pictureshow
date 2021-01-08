from unittest.mock import patch

import pytest

from pictureshow.core import PictureShow, _get_page_size_from_name
from pictureshow.exceptions import PageSizeError, LayoutError
from tests import PICS, A4_WIDTH, A4_LENGTH, A4, A4_LANDSCAPE

A4_PORTRAIT_MARGIN_72 = (A4_WIDTH - 144, A4_LENGTH - 144)
A4_LANDSCAPE_MARGIN_72 = (A4_LENGTH - 144, A4_WIDTH - 144)


class TestSavePdf:
    """Test core.PictureShow._save_pdf"""

    @patch('pictureshow.core.Canvas')
    @pytest.mark.parametrize(
        'pic_files, expected',
        (
            pytest.param(PICS._1_GOOD, (1, 0), id='1good'),
            pytest.param(PICS._2_GOOD, (2, 0), id='2good'),
            pytest.param(PICS._5_GOOD, (5, 0), id='5good'),
            pytest.param(PICS._3_TYPES, (3, 0), id='3types'),
            pytest.param(PICS._2_GOOD_1_BAD, (2, 1), id='2good1bad'),
            pytest.param(PICS._2_BAD_1_GOOD, (1, 2), id='2bad1good'),
            pytest.param(PICS._1_BAD, (0, 1), id='1bad'),
            pytest.param(PICS._2_BAD, (0, 2), id='2bad'),
            pytest.param(PICS.DIR, (0, 1), id='dir'),
            pytest.param(PICS.MISSING, (0, 1), id='missing'),
        )
    )
    def test_valid_and_invalid_input(self, mock_canvas_class, pic_files,
                                     expected):
        page_size, margin, layout, stretch_small = A4, 72, (1, 1), False
        fake_filename = 'foo'
        result = PictureShow(*pic_files)._save_pdf(
            fake_filename, page_size, margin, layout, stretch_small
        )
        assert result == expected
        mock_canvas_class.assert_called_once_with(fake_filename,
                                                  pagesize=page_size)

        # test the mocked canvas' method calls
        mock_canvas = mock_canvas_class()
        num_valid_pics = expected[0]
        if num_valid_pics > 0:
            mock_canvas.drawImage.assert_called()
            assert mock_canvas.drawImage.call_count == num_valid_pics
            mock_canvas.showPage.assert_called_with()
            assert mock_canvas.showPage.call_count == num_valid_pics
            mock_canvas.save.assert_called_once_with()
        else:
            mock_canvas.drawImage.assert_not_called()
            mock_canvas.showPage.assert_not_called()
            mock_canvas.save.assert_not_called()


class TestValidateLayout:
    """Test core.PictureShow._validate_layout"""

    @pytest.mark.parametrize(
        'layout, expected',
        (
            pytest.param((1, 1), (1, 1), id='(1, 1)'),
            pytest.param([1, 1], (1, 1), id='[1, 1]'),
            pytest.param((2, 3), (2, 3), id='(2, 3)'),
            pytest.param(iter([4, 3]), (4, 3), id='iter([4, 3])'),
            pytest.param('1x1', (1, 1), id='1x1'),
            pytest.param('010x005', (10, 5), id='010x005'),
            pytest.param(' 1 x 1 ', (1, 1), id=' 1 x 1 '),
        )
    )
    def test_valid_input(self, layout, expected):
        result = PictureShow._validate_layout(layout)
        assert result == expected

    @pytest.mark.parametrize(
        'layout',
        (
            pytest.param((1,), id='(1,)'),
            pytest.param('1', id='1'),
            pytest.param((1, 1, 1), id='(1, 1, 1)'),
            pytest.param('1x1x1', id='1x1x1'),
            pytest.param((0, 1), id='(0, 1)'),
            pytest.param('0x1', id='0x1'),
            pytest.param((-1, 3), id='(-1, 3)'),
            pytest.param('-1x3', id='-1x3'),
            pytest.param((1, 0.5), id='(1, 0.5)'),
            pytest.param('1x0.5', id='1x0.5'),
            pytest.param(0, id='0'),
            pytest.param(object(), id='object()'),
        )
    )
    def test_invalid_input_raises_error(self, layout):
        with pytest.raises(LayoutError, match='two positive integers expected'):
            PictureShow._validate_layout(layout)


class TestValidPictures:
    """Test core.PictureShow._valid_pictures"""

    @pytest.mark.parametrize(
        'mock_side_effects, expected',
        (
            pytest.param(['1ok'], ['1ok'], id='1 valid'),
            pytest.param(['1ok', '2ok'], ['1ok', '2ok'], id='2 valid'),
            pytest.param([ValueError], [], id='1 invalid'),
            pytest.param([ValueError, ValueError], [], id='2 invalid'),
            pytest.param(['1ok', ValueError, '2ok'], ['1ok', '2ok'],
                         id='2 valid + 1 invalid'),
            pytest.param([ValueError, '1ok', ValueError], ['1ok'],
                         id='2 invalid + 1 valid'),
            pytest.param([IsADirectoryError], [], id='dir'),
            pytest.param([FileNotFoundError], [], id='missing'),
        )
    )
    def test_typical_cases(self, mock_side_effects, expected):
        fake_filenames = ['foo'] * len(mock_side_effects)
        pic_show = PictureShow(*fake_filenames)
        with patch('pictureshow.core.ImageReader',
                   side_effect=mock_side_effects) as mock:
            result = list(pic_show._valid_pictures())
            mock.assert_called_with('foo')
            assert mock.call_count == len(fake_filenames)

        assert result == expected
        assert pic_show.errors == len(fake_filenames) - len(expected)


class TestPositionAndSize:
    """Test core.PictureShow._position_and_size"""

    @pytest.mark.parametrize(
        'pic_size, area_size',
        (
            pytest.param((800, 387), A4_PORTRAIT_MARGIN_72, id='portrait'),
            pytest.param((800, 387), A4_LANDSCAPE_MARGIN_72, id='landscape'),
            pytest.param((1000, 1500), A4_PORTRAIT_MARGIN_72, id='2:3 portrait'),
            pytest.param(
                (1500, 1000),
                A4_LANDSCAPE_MARGIN_72,
                id='3:2 landscape',
                marks=pytest.mark.xfail(
                    raises=AssertionError,
                    reason='picture is wider than page, but not wider than area'
                )
            ),
        )
    )
    def test_big_wide_picture(self, pic_size, area_size):
        aspect_ratio = pic_size[0] / pic_size[1]
        area_width, area_height = area_size
        x, y, pic_width, pic_height = PictureShow._position_and_size(
            pic_size, area_size, stretch_small=False
        )
        assert x == 0
        assert y == (area_height - pic_height) / 2
        assert pic_width == area_width
        assert pic_height == pytest.approx(pic_width / aspect_ratio)

    @pytest.mark.parametrize(
        'pic_size, area_size',
        (
            pytest.param((400, 3260), A4_PORTRAIT_MARGIN_72, id='portrait'),
            pytest.param((400, 3260), A4_LANDSCAPE_MARGIN_72, id='landscape'),
            pytest.param((1500, 1000), A4_LANDSCAPE_MARGIN_72, id='3:2 landscape'),
            pytest.param(
                (1000, 1500),
                A4_PORTRAIT_MARGIN_72,
                id='2:3 portrait',
                marks=pytest.mark.xfail(
                    raises=AssertionError,
                    reason='picture is taller than page, but not taller than area'
                )
            ),
        )
    )
    def test_big_tall_picture(self, pic_size, area_size):
        aspect_ratio = pic_size[0] / pic_size[1]
        area_width, area_height = area_size
        x, y, pic_width, pic_height = PictureShow._position_and_size(
            pic_size, area_size, stretch_small=False
        )
        assert x == (area_width - pic_width) / 2
        assert y == 0
        assert pic_width == pytest.approx(pic_height * aspect_ratio)
        assert pic_height == area_height

    @pytest.mark.parametrize(
        'pic_size, area_size',
        (
            pytest.param((104, 112), A4_PORTRAIT_MARGIN_72, id='portrait'),
            pytest.param((104, 112), A4_LANDSCAPE_MARGIN_72, id='landscape'),
        )
    )
    def test_small_picture(self, pic_size, area_size):
        area_width, area_height = area_size
        x, y, pic_width, pic_height = PictureShow._position_and_size(
            pic_size, area_size, stretch_small=False
        )
        assert x == (area_width - pic_width) / 2
        assert y == (area_height - pic_height) / 2
        assert pic_width, pic_height == pic_size

    @pytest.mark.parametrize(
        'pic_size, area_size',
        (
            pytest.param((192, 108), A4_PORTRAIT_MARGIN_72, id='portrait'),
            pytest.param((192, 108), A4_LANDSCAPE_MARGIN_72, id='landscape'),
            pytest.param((200, 300), A4_PORTRAIT_MARGIN_72, id='2:3 portrait'),
            pytest.param(
                (300, 200),
                A4_LANDSCAPE_MARGIN_72,
                id='3:2 landscape',
                marks=pytest.mark.xfail(
                    raises=AssertionError,
                    reason='picture is wider than page, but not wider than area'
                )
            ),
        )
    )
    def test_small_wide_picture_stretch_small(self, pic_size, area_size):
        aspect_ratio = pic_size[0] / pic_size[1]
        area_width, area_height = area_size
        x, y, pic_width, pic_height = PictureShow._position_and_size(
            pic_size, area_size, stretch_small=True
        )
        assert x == 0
        assert y == (area_height - pic_height) / 2
        assert pic_width == area_width
        assert pic_height == pytest.approx(pic_width / aspect_ratio)

    @pytest.mark.parametrize(
        'pic_size, area_size',
        (
            pytest.param((68, 112), A4_PORTRAIT_MARGIN_72, id='portrait'),
            pytest.param((68, 112), A4_LANDSCAPE_MARGIN_72, id='landscape'),
            pytest.param((300, 200), A4_LANDSCAPE_MARGIN_72, id='3:2 landscape'),
            pytest.param(
                (200, 300),
                A4_PORTRAIT_MARGIN_72,
                id='2:3 portrait',
                marks=pytest.mark.xfail(
                    raises=AssertionError,
                    reason='picture is taller than page, but not taller than area'
                )
            ),
        )
    )
    def test_small_tall_picture_stretch_small(self, pic_size, area_size):
        aspect_ratio = pic_size[0] / pic_size[1]
        area_width, area_height = area_size
        x, y, pic_width, pic_height = PictureShow._position_and_size(
            pic_size, area_size, stretch_small=True
        )
        assert x == (area_width - pic_width) / 2
        assert y == 0
        assert pic_width == pytest.approx(pic_height * aspect_ratio)
        assert pic_height == area_height


class TestAreas:
    """Test core.PictureShow._areas"""

    @pytest.mark.parametrize(
        'layout, expected_height',
        (
            pytest.param((1, 1), A4_LENGTH - 2*72, id='1x1'),
            pytest.param((1, 2), (A4_LENGTH - 3*72) / 2, id='1x2'),
            pytest.param((1, 3), (A4_LENGTH - 4*72) / 3, id='1x3'),
            pytest.param((1, 4), (A4_LENGTH - 5*72) / 4, id='1x4'),
        )
    )
    def test_single_column_layout(self, layout, expected_height):
        page_size, margin = A4, 72
        areas = list(PictureShow._areas(layout, page_size, margin))

        # number of areas == number of rows
        assert len(areas) == layout[1]

        # the bottom-most area on page has y == margin
        assert areas[-1].y == pytest.approx(margin)

        # all areas have x == margin, width == A4_WIDTH - 2*margin
        assert all(area == pytest.approx(
            (margin, A4_LENGTH - i * (expected_height + margin),
             A4_WIDTH - 2*margin, expected_height),
            abs=1e-4
        )
                   for i, area in enumerate(areas, 1))

    @pytest.mark.parametrize(
        'layout, expected_width',
        (
            pytest.param((1, 1), A4_WIDTH - 144, id='1x1'),
            pytest.param((2, 1), (A4_WIDTH - 216) / 2, id='2x1'),
            pytest.param((3, 1), (A4_WIDTH - 288) / 3, id='3x1'),
            pytest.param((4, 1), (A4_WIDTH - 360) / 4, id='4x1'),
        )
    )
    def test_single_row_layout(self, layout, expected_width):
        page_size, margin = A4, 72
        areas = list(PictureShow._areas(layout, page_size, margin))

        # number of areas == number of columns
        assert len(areas) == layout[0]

        # the left-most area on page has x == margin
        assert areas[0].x == pytest.approx(margin)

        # all areas have y == margin, height == A4_LENGTH - 2*margin
        assert all(area == pytest.approx(
            (margin + i * (margin + expected_width), margin,
             expected_width, A4_LENGTH - 2*margin),
            abs=1e-4
        )
                   for i, area in enumerate(areas))

    @pytest.mark.parametrize(
        'layout, page_size, margin, expected_width, expected_height',
        (
            pytest.param((3, 3), A4, 18, (A4_WIDTH - 72) / 3,
                         (A4_LENGTH - 72) / 3, id='(3, 3) portrait'),
            pytest.param((3, 3), A4, 0, A4_WIDTH / 3, A4_LENGTH / 3,
                         id='(3, 3) portrait no margin'),
            pytest.param((3, 3), A4_LANDSCAPE, 36, (A4_LENGTH - 144) / 3,
                         (A4_WIDTH - 144) / 3, id='(3, 3) landscape'),
        )
    )
    def test_3x3_layout(self, layout, page_size, margin, expected_width,
                        expected_height):
        areas = list(PictureShow._areas(layout, page_size, margin))
        assert len(areas) == 9
        assert all(area.width == pytest.approx(expected_width, abs=1e-4)
                   for area in areas)
        assert all(area.height == pytest.approx(expected_height, abs=1e-4)
                   for area in areas)

        # all areas in the left column have x == margin
        assert all(area.x == pytest.approx(margin) for area in areas[::3])

        # all areas in the bottom row have y == margin
        assert all(area.y == pytest.approx(margin) for area in areas[6:])


class TestGetPageSizeFromName:
    """Test core._get_page_size_from_name"""

    @pytest.mark.parametrize(
        'name, expected_mm',
        (
            pytest.param('A4', [210, 297], id='A4'),
            pytest.param('A5', [148, 210], id='A5'),
            pytest.param('a4', [210, 297], id='a4'),
            pytest.param('b0', [1000, 1414], id='b0'),
        )
    )
    def test_valid_names_mm(self, name, expected_mm):
        result = _get_page_size_from_name(name)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert [n / 72 * 25.4 for n in result] == pytest.approx(expected_mm)

    @pytest.mark.parametrize(
        'name, expected_inches',
        (
            pytest.param('LETTER', [8.5, 11], id='LETTER'),
            pytest.param('letter', [8.5, 11], id='letter'),
            pytest.param('LEGAL', [8.5, 14], id='LEGAL'),
            pytest.param('legal', [8.5, 14], id='legal'),
        )
    )
    def test_valid_names_inches(self, name, expected_inches):
        result = _get_page_size_from_name(name)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert [n / 72 for n in result] == pytest.approx(expected_inches)

    @pytest.mark.parametrize(
        'name',
        (
            pytest.param('A11', id='A11'),
            pytest.param('landscape', id='landscape'),
            pytest.param('portrait', id='portrait'),
        )
    )
    def test_invalid_name_raises_error(self, name):
        with pytest.raises(PageSizeError, match='unknown page size: .+'):
            _get_page_size_from_name(name)
