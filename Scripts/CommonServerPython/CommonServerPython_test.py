# -*- coding: utf-8 -*-
from CommonServerPython import *

import copy
import unittest

INFO = {'b': 1,
        'a': {
            'safd': 3,
            'b': [
                {'c': {'d': 432}, 'd': 2},
                {'c': {'f': 1}},
                {'b': 1234},
                {'c': {'d': 4567}},
                {'c': {'d': 11}},
                {'c': {'d': u'asdf'}}],
            'c': {'d': 10},
        }
        }


def test_xml():
    import json

    xml = "<work><employee><id>100</id><name>foo</name></employee><employee><id>200</id><name>goo</name>" \
          "</employee></work>"
    jsonExpected = '{"work": {"employee": [{"id": "100", "name": "foo"}, {"id": "200", "name": "goo"}]}}'

    jsonActual = xml2json(xml)
    assert jsonActual == jsonExpected, "expected\n" + jsonExpected + "\n to equal \n" + jsonActual

    jsonDict = json.loads(jsonActual)
    assert jsonDict['work']['employee'][0]['id'] == "100", 'id of first employee must be 100'
    assert jsonDict['work']['employee'][1]['name'] == "goo", 'name of second employee must be goo'

    xmlActual = json2xml(jsonActual)
    assert xmlActual == xml, "expected\n" + xml + "\n to equal \n" + xmlActual


def toEntry(table):
    return {

        'Type': entryTypes['note'],
        'Contents': table,
        'ContentsFormat': formats['table'],
        'ReadableContentsFormat': formats['markdown'],
        'HumanReadable': table
    }


def test_tbl_to_md():
    tables = []
    data = [
        {
            'header_1': 'a1',
            'header_2': 'b1',
            'header_3': 'c1'
        },
        {
            'header_1': 'a2',
            'header_2': 'b2',
            'header_3': 'c2'
        },
        {
            'header_1': 'a3',
            'header_2': 'b3',
            'header_3': 'c3'
        },
    ]

    # sanity
    table = tableToMarkdown('tableToMarkdown test', data)
    expected_table = '''### tableToMarkdown test
|header_2|header_3|header_1|
|---|---|---|
|b1|c1|a1|
|b2|c2|a2|
|b3|c3|a3|
'''
    tables.append((table, expected_table, ))

    # header transform
    table_transform = tableToMarkdown('tableToMarkdown test with headerTransform', data,
                                      headerTransform=underscoreToCamelCase)
    expected_table_transform = '''### tableToMarkdown test with headerTransform
|Header2|Header3|Header1|
|---|---|---|
|b1|c1|a1|
|b2|c2|a2|
|b3|c3|a3|
'''
    tables.append((table_transform, expected_table_transform, ))

    # escaping characters: multiline + md-chars
    data2 = copy.deepcopy(data)
    for i, d in enumerate(data2):
        d['header_2'] = 'b%d.1\nb%d.2' % (i + 1, i + 1, )
        d['header_3'] = 'c%d|1' % (i + 1, )

    table_multiline = tableToMarkdown('tableToMarkdown test with multiline', data2)
    expected_table_multiline = '''### tableToMarkdown test with multiline
|header_2|header_3|header_1|
|---|---|---|
|b1.1<br>b1.2|c1\|1|a1|
|b2.1<br>b2.2|c2\|1|a2|
|b3.1<br>b3.2|c3\|1|a3|
'''
    tables.append((table_multiline, expected_table_multiline, ))

    # url + empty data
    data3 = copy.deepcopy(data)
    for i, d in enumerate(data3):
        d['header_3'] = '[url](https:\\demisto.com)'
        d['header_2'] = None
    table_url_missing_info = tableToMarkdown('tableToMarkdown test with url and missing info', data3)
    expected_table_url_missing_info = '''### tableToMarkdown test with url and missing info
|header_2|header_3|header_1|
|---|---|---|
||[url](https:\\demisto.com)|a1|
||[url](https:\\demisto.com)|a2|
||[url](https:\\demisto.com)|a3|
'''
    tables.append((table_url_missing_info, expected_table_url_missing_info, ))

    # single column table
    table_single_column = tableToMarkdown('tableToMarkdown test with single column', data, ['header_1'])
    expected_table_single_column = '''### tableToMarkdown test with single column
|header_1|
|---|
|a1|
|a2|
|a3|
'''
    tables.append((table_single_column, expected_table_single_column, ))

    # list values
    data4 = copy.deepcopy(data)
    for i, d in enumerate(data4):
        d['header_3'] = [i + 1, 'second item']
        d['header_2'] = 'hi'
    table_list_field = tableToMarkdown('tableToMarkdown test with list field', data4)
    expected_table_list_field = '''### tableToMarkdown test with list field
|header_2|header_3|header_1|
|---|---|---|
|hi|1,<br>second item|a1|
|hi|2,<br>second item|a2|
|hi|3,<br>second item|a3|
'''
    tables.append((table_list_field, expected_table_list_field, ))

    # all fields are empty
    data5 = [
        {
            'a': None,
            'b': None,
            'c': None,
        } for _ in range(3)
    ]
    table_all_none = tableToMarkdown('tableToMarkdown test with all none fields', data5)
    expected_table_all_none = '''### tableToMarkdown test with all none fields
|a|c|b|
|---|---|---|
||||
||||
||||
'''
    tables.append((table_all_none, expected_table_all_none, ))

    # all fields are empty - removed
    table_all_none2 = tableToMarkdown('tableToMarkdown test with all none fields2', data5, removeNull=True)
    expected_table_all_none2 = '''### tableToMarkdown test with all none fields2
**No entries.**
'''
    tables.append((table_all_none2, expected_table_all_none2, ))

    # header not on first object
    data6 = copy.deepcopy(data)
    data6[1]['extra_header'] = 'sample'
    table_extra_header = tableToMarkdown('tableToMarkdown test with extra header', data6,
                                         headers=['header_1', 'header_2', 'extra_header'])
    expected_table_extra_header = '''### tableToMarkdown test with extra header
|header_1|header_2|extra_header|
|---|---|---|
|a1|b1||
|a2|b2|sample|
|a3|b3||
'''
    tables.append((table_extra_header, expected_table_extra_header, ))

    # no such header
    table_no_headers = tableToMarkdown('tableToMarkdown test with no headers', data,
                                       headers=['no', 'header', 'found'], removeNull=True)
    expected_table_no_headers = '''### tableToMarkdown test with no headers
**No entries.**
'''
    tables.append((table_no_headers, expected_table_no_headers, ))

    # dict value
    data7 = copy.deepcopy(data)
    data7[1]['extra_header'] = {'sample': 'qwerty', 'sample2': 'asdf'}
    table_dict_record = tableToMarkdown('tableToMarkdown test with dict record', data7,
                                        headers=['header_1', 'header_2', 'extra_header'])
    expected_dict_record = '''### tableToMarkdown test with dict record
|header_1|header_2|extra_header|
|---|---|---|
|a1|b1||
|a2|b2|sample: qwerty<br>sample2: asdf|
|a3|b3||
'''
    tables.append((table_dict_record, expected_dict_record, ))

    # string header (instead of list)
    table_string_header = tableToMarkdown('tableToMarkdown string header', data, 'header_1')
    expected_string_header_tbl = '''### tableToMarkdown string header
|header_1|
|---|
|a1|
|a2|
|a3|
'''
    tables.append((table_string_header, expected_string_header_tbl, ))

    # list of string values instead of list of dict objects
    table_string_array = tableToMarkdown('tableToMarkdown test with string array', ['foo', 'bar', 'katz'], ['header_1'])
    expected_string_array_tbl = '''### tableToMarkdown test with string array
|header_1|
|---|
|foo|
|bar|
|katz|
'''
    tables.append((table_string_array, expected_string_array_tbl, ))

    # combination: string header + string values list
    table_string_array_string_header = tableToMarkdown('tableToMarkdown test with string array and string header',
                                                       ['foo', 'bar', 'katz'], 'header_1')
    expected_string_array_string_header_tbl = '''### tableToMarkdown test with string array and string header
|header_1|
|---|
|foo|
|bar|
|katz|
'''
    tables.append((table_string_array_string_header, expected_string_array_string_header_tbl, ))

    results = [actual == expected for actual, expected in tables]

    assert results, results


def test_flatten_cell():
    returned = []

    # sanity
    utf8_to_flatten = 'abcdefghijklmnopqrstuvwxyz1234567890!'.decode('utf8')
    flatten_text = flattenCell(utf8_to_flatten)
    expected_string = 'abcdefghijklmnopqrstuvwxyz1234567890!'

    returned.append((flatten_text, expected_string))

    # list of uft8 and string to flatten
    str_a = 'abcdefghijklmnopqrstuvwxyz1234567890!'
    utf8_b = str_a.decode('utf8')
    list_to_flatten = [str_a, utf8_b]
    flatten_text = flattenCell(list_to_flatten)
    expected_flatten_string = 'abcdefghijklmnopqrstuvwxyz1234567890!,\nabcdefghijklmnopqrstuvwxyz1234567890!'

    returned.append((flatten_text, expected_flatten_string))

    # special character test
    special_char = u'会'
    list_of_special = [special_char, special_char]
    try:
        flattenCell(list_of_special)
        flattenCell(special_char)
    except Exception:
        demisto.results(toEntry('special character failure - flatten_cell'))
        demisto.results(return_error('failure'))

    # dictionary test
    dict_to_flatten = {'first': u'会'}
    expected_flatten_dict = u'{\n    "first": "\u4f1a"\n}'
    returned.append((dict_to_flatten, expected_flatten_dict))

    results = [actual == expected for actual, expected in returned]

    assert results, results


def test_hash_djb2():
    assert hash_djb2("test") == 2090756197, "Invalid value of hash_djb2"


def test_camelize():
    non_camalized = [{'chookity_bop': 'asdasd'}, {'ab_c': 'd e', 'fgh_ijk': 'lm', 'nop': 'qr_st'}]
    expected_output = "[{u'ChookityBop': 'asdasd'}, {u'AbC': 'd e', u'Nop': 'qr_st', u'FghIjk': 'lm'}]"
    assert str(camelize(non_camalized, '_')) == expected_output

    non_camalized2 = {'ab_c': 'd e', 'fgh_ijk': 'lm', 'nop': 'qr_st'}
    expected_output2 = "{u'AbC': 'd e', u'Nop': 'qr_st', u'FghIjk': 'lm'}"
    assert str(camelize(non_camalized2, '_')) == expected_output2


def test_date_to_timestamp():
    assert date_to_timestamp('2018-11-06T08:56:41') == 1541494601000
    assert date_to_timestamp(datetime.strptime('2018-11-06T08:56:41', "%Y-%m-%dT%H:%M:%S")) == 1541494601000


def test_pascalToSpace():
    use_cases = [
        ('Validate', 'Validate'),
        ('validate', 'Validate'),
        ('TCP', 'TCP'),
        ('eventType', 'Event Type'),
        ('eventID', 'Event ID'),
        ('eventId', 'Event Id'),
        ('IPAddress', 'IP Address'),
    ]
    for s, expected in use_cases:
        assert pascalToSpace(s) == expected, 'Error on {} != {}'.format(pascalToSpace(s), expected)


def test_argToList():
    expected = ['a', 'b', 'c']
    test1 = ['a', 'b', 'c']
    test2 = 'a,b,c'
    test3 = '["a","b","c"]'
    test4 = 'a;b;c'

    results = [argToList(test1), argToList(test2), argToList(test2, ','), argToList(test3), argToList(test4, ';')]

    for result in results:
        assert expected == result, 'argToList test failed, {} is not equal to {}'.format(str(result), str(expected))


def test_return_outputs():
    return_outputs(readable_output="foo", outputs={"foo": "foo1"})

    return_outputs(readable_output='', outputs={"foo": "foo1"})

    return_outputs(readable_output="foo", outputs={})

    return_outputs("foo", {"foo": "foo1"}, raw_response={"raw": "response"})


def test_remove_nulls():
    temp_dictionary = {"a": "b", "c": 4, "e": [], "f": {}, "g": None, "h": "", "i": [1], "k": ()}
    expected_dictionary = {"a": "b", "c": 4, "i": [1]}

    remove_nulls_from_dictionary(temp_dictionary)

    assert expected_dictionary == temp_dictionary, \
        "remove_nulls_from_dictionary test failed, {} is not equal to {}".format(str(temp_dictionary),
                                                                                 str(expected_dictionary))


def test_append_context():
    appendContext('empty_string_key', '')
    appendContext('empty_list_key', [])
    appendContext('zero_key', 0)
    appendContext('none_key', None)
    demisto.results("placeholder so the run would finish")


class TestIsError(unittest.TestCase):

    def test_is_error_true(self):
        execute_command_results = [
            {
                "Type": entryTypes["error"],
                "ContentsFormat": formats["text"],
                "Contents": "this is error message"
            }
        ]
        self.assertTrue(is_error(execute_command_results))

    def test_is_error_single_entry(self):
        execute_command_results = {
            "Type": entryTypes["error"],
            "ContentsFormat": formats["text"],
            "Contents": "this is error message"
        }

        self.assertTrue(is_error(execute_command_results))

    def test_is_error_false(self):
        execute_command_results = [
            {
                "Type": entryTypes["note"],
                "ContentsFormat": formats["text"],
                "Contents": "this is regular note"
            }
        ]
        self.assertFalse(is_error(execute_command_results))

    def test_not_error_entry(self):
        execute_command_results = "invalid command results as string"
        self.assertFalse(is_error(execute_command_results))


class TestGetError(unittest.TestCase):
    def test_get_error(self):
        execute_command_results = [
            {
                "Type": entryTypes["error"],
                "ContentsFormat": formats["text"],
                "Contents": "this is error message"
            }
        ]
        error = get_error(execute_command_results)
        self.assertEquals(error, "this is error message")

    def test_get_error_single_entry(self):
        execute_command_results = {
            "Type": entryTypes["error"],
            "ContentsFormat": formats["text"],
            "Contents": "this is error message"
        }

        error = get_error(execute_command_results)
        self.assertEquals(error, "this is error message")

    def test_get_error_need_raise_error_on_non_error_input(self):
        execute_command_results = [
            {
                "Type": entryTypes["note"],
                "ContentsFormat": formats["text"],
                "Contents": "this is not an error"
            }
        ]
        try:
            get_error(execute_command_results)
            self.fail("get_error should raise an error")
        except ValueError as e:
            self.assertEquals(e.message,
                              "execute_command_result has no error entry. before using get_error use is_error")
