from glob import glob
from json import load
from messages import print_error, print_info
from os.path import basename


def version_to_array(version, dbtype):
    """ Convert a version string to a version array, or return an empty string if
        the original string was empty

    Keyword arguments:
    version -- A string with a dot separated version
    dbtype  -- A string with the database type (postgresql|mssql)
    """
    if version != '':
        version = version.split('.')
        for i in range(0, len(version)):
            version[i] = int(version[i])
    # To be able to work with MSSQL 2000 and 7.0,
    # see https://sqlserverbuilds.blogspot.ru/
    if dbtype == 'mssql':
        if len(version) == 3:
            version.append(0)
    return(version)


def check_ver(conn, min_ver, max_ver, dbtype):
    """ Check SQL server version against test required max and min versions.

    Keyword arguments:
    conn    -- A db connection (according to Python DB API v2.0)
    min_ver -- A string with the minimum version required
    max_ver -- A string with the maximum version required
    dbtype  -- A string with the database type (postgresql|mssql)
    """
    cursor = conn.cursor()
    if dbtype == 'postgresql':
        sentence = 'SELECT setting FROM pg_settings WHERE name = \'server_version\';'
    elif dbtype == 'mssql':
        sentence = 'SELECT serverproperty(\'ProductVersion\');'
    cursor.execute(sentence)
    server_ver = cursor.fetchone()[0]
    cursor.close()
    min_ver = version_to_array(min_ver, dbtype)
    max_ver = version_to_array(max_ver, dbtype)
    server_ver = version_to_array(server_ver, dbtype)
    if server_ver >= min_ver and (server_ver <= max_ver or min_ver == ''):
        return(True)
    else:
        return(False)


def run_tests(path, conn, replaces, dbtype):
    """Run SQL tests over a connection, returns a dict with results.

    Keyword arguments:
    path     -- String with the path having the SQL files for tests
    conn     -- A db connection (according to Python DB API v2.0)
    replaces -- A dict with replaces to perform at testing code
    dbtype   -- A string with the database type (postgresql|mssql)
    """
    files = sorted(glob(path))
    tests = {'total': 0, 'ok': 0, 'errors': 0}
    for fname in files:
        test_file = open('%s.json' % fname.rsplit('.', 1)[0], 'r')
        test_properties = load(test_file)
        test_desc = test_properties['test_desc']
        test_number = basename(fname).split('_')[0]
        req_ver = test_properties['server']['version']
        if check_ver(conn, req_ver['min'], req_ver['max'], dbtype):
            tests['total'] += 1
            f = open(fname, 'r')
            sentence = f.read()
            for key, elem in replaces.items():
                sentence = sentence.replace(key, elem)
            print_info("%s: Testing %s" % (test_number, test_desc))
            try:
                cursor = conn.cursor()
                cursor.execute(sentence)
                conn.commit()
                cursor.close()
                tests['ok'] += 1
            except Exception as e:
                print_error("Error running %s (%s)" % (test_desc, fname))
                try:
                    print_error(e.pgcode)
                    print_error(e.pgerror)
                except:
                    print_error(e)
                conn.rollback()
                tests['errors'] += 1
            f.close()
    return(tests)
