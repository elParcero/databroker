from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import six
from metadataStore.odm_templates import (BeginRunEvent, BeamlineConfig,
                                         EndRunEvent, EventDescriptor, Event)
import datetime
from metadataStore.conf import host, port, database
from mongoengine import connect


def insert_begin_run(time, beamline_id, beamline_config=None, owner=None,
                   scan_id=None, custom=None):
    """ Provide a head for a sequence of events. Entry point for an
    experiment's run.

    Parameters
    ----------
    time : float
        The date/time as found at the client side when an event is
        created.
    beamline_id: str
        Beamline String identifier. Not unique, just an indicator of
        beamline code for multiple beamline systems
    owner: str, optional
        Specifies the unix user credentials of the user creating the entry
    scan_id : int, optional
        Unique scan identifier visible to the user and data analysis
    beamline_config: metadataStore.odm_temples.BeamlineConfig, optional
        Foreign key to beamline config corresponding to a given run
    custom: dict, optional
        Additional parameters that data acquisition code/user wants to
        append to a given header. Name/value pairs
    Returns
    -------
    begin_run: mongoengine.Document
        Inserted mongoengine object
    """
    connect(db=database, host=host, port=port)

    begin_run = BeginRunEvent(time=time, scan_id=scan_id, owner=owner,
                              time_as_datetime=__convert2datetime(time),
                              beamline_id=beamline_id, custom=custom)

    if beamline_config is not None:
        begin_run.beamline_config = beamline_config.id

    begin_run.save(validate=True, write_concern={"w": 1})

    return begin_run


def insert_end_run(begin_run_event, time, reason=None):
    """ Provide an end to a sequence of events. Exit point for an
    experiment's run.

    Parameters
    ----------
    begin_run_event : metadataStore.odm_temples.BeginRunEvent
        Foreign key to corresponding BeginRunEvent
    reason : str
        provides information regarding the run success.
    time : timestamp
        The date/time as found at the client side when an event is
        created.

    Returns
    -------
    begin_run: mongoengine.Document
        Inserted mongoengine object
    """
    connect(db=database, host=host, port=port)

    begin_run = EndRunEvent(begin_run_event=begin_run_event.id, reason=reason,
                            time=time,
                            time_as_datetime=__convert2datetime(time))

    begin_run.save(validate=True, write_concern={"w": 1})

    return begin_run


def insert_beamline_config(config_params=None):
    """ Create a beamline_config  in metadataStore database backend

    Parameters
    ----------
    config_params : dict
        Name/value pairs that indicate beamline configuration
        parameters during capturing of data

    Returns
    -------
    blc : BeamlineConfig
        The document added to the collection
    """

    connect(db=database, host=host, port=port)

    beamline_config = BeamlineConfig(config_params=config_params)
    beamline_config.save(validate=True, write_concern={"w": 1})

    return beamline_config


def insert_event_descriptor(begin_run_event, data_keys, time, event_type=None):
    """ Create an event_descriptor in metadataStore database backend

    Parameters
    ----------
    begin_run_event: metadataStore.odm_templates.BeginRunEvent
        BeginRunEvent object created prior to a BeginRunEvent
    data_keys : dict
        Provides information about keys of the data dictionary in
        an event will contain

    Returns
    -------
    ev_desc : EventDescriptor
        The document added to the collection.

    """
    connect(db=database, host=host, port=port)

    event_descriptor = EventDescriptor(begin_run_event=begin_run_event.id,
                                       data_keys=data_keys, time=time,
                                       event_type=event_type,
                                       time_as_datetime=__convert2datetime(time))

    event_descriptor = __replace_descriptor_data_key_dots(event_descriptor,
                                                          direction='in')

    event_descriptor.save(validate=True, write_concern={"w": 1})

    return event_descriptor


def insert_event(event_descriptor, time, data, seq_no):
    """Create an event in metadataStore database backend

    Parameters
    ----------
    event_descriptor : metadataStore.odm_templates.EventDescriptor
        EventDescriptor object that specific event entry is going
        to point(foreign key)
    data : dict
        Dictionary that contains the name value fields for the data associated
        with an event
    time : timestamp
        The date/time as found at the client side when an event is
        created.
    seq_no : int
        Unique sequence number for the event. Provides order of an event in
        the group of events
    """

    #TODO: seq_no is not optional according to opyhd folks. To be discussed!!

    connect(db=database, host=host, port=port)
    event = Event(descriptor_id=event_descriptor.id,
                  data=data, time=time, seq_no=seq_no,
                  time_as_datetime=__convert2datetime(time))

    event = __replace_event_data_key_dots(event, direction='in')

    event.save(validate=True, write_concern={"w": 1})

    return event


def find_begin_run(limit=50, **kwargs):
    """ Given search criteria, locate the BeginRunEvent object
    Parameters
    ----------

    limit: int
        Number of header objects to be returned

    Other Parameters
    ----------------

    scan_id : int
        Scan identifier. Not unique

    owner : str
        User name identifier associated with a scan

    create_time : dict
        header insert time. Keys must be start and end to
        give a range to the search

    beamline_id : str
        String identifier for a specific beamline

    unique_id : str
        Hashed unique identifier

    Usage
    ------

    >>> find_begin_run(scan_id=123)
    >>> find_begin_run(owner='arkilic')
    >>> find_begin_run(time={'start': 1421176750.514707,
    ...                      'end': time.time()})
    >>> find_begin_run(time={'start': 1421176750.514707,
    ...                      'end': time.time()})

    >>> find_begin_run(owner='arkilic', time={'start': 1421176750.514707,
    ...                                       'end': time.time()})

    """
    connect(db=database, host=host, port=port)
    search_dict = dict()

    try:
        search_dict['scan_id'] = kwargs.pop('scan_id')
    except KeyError:
        pass

    try:
        search_dict['unique_id'] = kwargs.pop('unique_id')
    except KeyError:
        pass

    try:
        search_dict['owner'] = kwargs.pop('owner')
    except KeyError:
        pass

    try:
        search_dict['beamline_id'] = kwargs.pop('beamline_id')
    except KeyError:
        pass

    try:
        time_dict = kwargs.pop('time')
        if not isinstance(time_dict, dict):
            raise ValueError('Wrong format. time must include '
                             'start and end keys for range. Must be a dict')
        else:
            if 'start' in time_dict and 'end' in time_dict:
                search_dict['time'] = {'$gte': time_dict['start'],
                                       '$lte': time_dict['end']}
            else:
                raise ValueError('time must include start '
                                 'and end keys for range search')
    except KeyError:
        pass

    if search_dict:
        br_objects = BeginRunEvent.objects(__raw__=search_dict).order_by('-_id')[:limit]
    else:
        br_objects = list()

    for begin_run in br_objects:
        #Need to make sure MongoEngine document class allows the below operation
        begin_run.event_descriptors = find_event_descriptor(begin_run)

    return br_objects


def find_beamline_config(_id):
    """Return beamline config objects given a unique mongo _id

    Parameters
    ----------
    _id: bson.ObjectId

    """
    connect(db=database, host=host, port=port)
    return BeamlineConfig.objects(id=_id).order_by('-_id')


def find_event_descriptor(begin_run_event):
    """Return beamline config objects given a unique mongo id

    Parameters
    ----------
    _id: bson.ObjectId

    """
    event_descriptor_list = list()
    connect(db=database, host=host, port=port)
    for event_descriptor in EventDescriptor.objects(begin_run_event=begin_run_event.id).order_by('-_id'):
        event_descriptor = __replace_descriptor_data_key_dots(event_descriptor,
                                                              direction='out')
        event_descriptor_list.append(event_descriptor)
    return event_descriptor_list


def fetch_events(limit=1000, **kwargs):
    """

    Parameters
    -----------
    limit: int
        number of events returned

    Other Parameters
    ----------------
    time: dict
        time of the event. dict keys must be start and end
    descriptor: mongoengine.Document
        event descriptor object
    """
    connect(db=database, host=host, port=port)

    search_dict = dict()
    try:
        time_dict = kwargs.pop('time')
        if not isinstance(time_dict, dict):
            raise ValueError('Wrong format. time must include '
                             'start and end keys for range. Must be a dict')
        else:
            if 'start' in time_dict and 'end' in time_dict:
                search_dict['time'] = {'$gte': time_dict['start'],
                                       '$lte': time_dict['end']}
            else:
                raise ValueError('time must include start '
                                 'and end keys for range search')
    except KeyError:
        pass

    try:
        desc = kwargs.pop('descriptor')
        search_dict['descriptor_id'] = desc.id
    except KeyError:
        pass
    result = Event.objects(__raw__=search_dict).order_by('-_id')[:limit]
    return result


def find_event(begin_run_event, limit=1000):
    """Returns a set of events given a BeginRunEvent object

    Parameters
    ---------
    begin_run_event: mongoengine.Document
        BeginRunEvent object that events possibly fall under
    limit: int
        Number of headers to be returned

    Returns
    -------
    events: list
        Set of events encapsulated within a BeginRunEvent's scope


    """
    connect(db=database, host=host, port=port)
    events = list()
    descriptors = EventDescriptor.objects(begin_run_id=begin_run_event.id)
    for descriptor in descriptors:
        events.append(find_event_given_descriptor(descriptor))

    return events


def find_event_given_descriptor(event_descriptor):
    """Return all Event(s) associated with an EventDescriptor

    Parameters
    ----------

    event_descriptor: metadataStore.database.EventDescriptor
    EventDescriptor instance

    """
    connect(db=database, host=host, port=port)
    event_list = list()
    for event in Event.objects(
            descriptor=event_descriptor.id).order_by('-_id'):
        event = __replace_event_data_key_dots(event, direction='out')
        event_list.append(event)

    return event_list


def find(data=True, limit=50, **kwargs):
    """
    Returns dictionary of objects
    Headers keyed on unique scan_id in header_scan_id format
    data flag is set to True by default since users
    intuitively expect data back

    Parameters
    ---------

    scan_id: int

    owner: str

    beamline_id: str

    status: str

    create_time: dict
    create_time={'start': float, 'end': float}

    """
    header_objects = find_begin_run(limit, **kwargs)

    if data:
        beamline_config_objects = dict()
        event_descriptor_objects = dict()
        event_objects = dict()
        if header_objects:
            for header in header_objects:
                event_objects[header.id] = find_event(header)
    return header_objects, event_objects


def find_last():
    """Indexed on ObjectId NOT end_time.

    Returns the last created header not modified!!

    Returns
    -------

    header: metadataStore.database.header.Header
        Returns the last header created. DOES NOT RETURN THE EVENTS.


    """
    connect(db=database, host=host, port=port)

    return BeginRunEvent.objects.order_by('-_id')[0:1][0]


def __convert2datetime(time_stamp):
    if isinstance(time_stamp, float):
        return datetime.datetime.fromtimestamp(time_stamp)
    else:
        raise TypeError('Timestamp format is not correct!')


def __replace_dict_keys(input_dict, src, dst):
    """
    Helper function to replace forbidden chars in dictionary keys

    Parameters
    ----------
    input_dict : dict
        The dict to have it's keys replaced

    src : str
        the string to be replaced

    dst : str
        The string to replace the src string with

    Returns
    -------
    ret : dict
        The dictionary with all instances of 'src' in the key
        replaced with 'dst'

    """
    return {k.replace(src, dst): v for
            k, v in six.iteritems(input_dict)}


def __src_dst(direction):
    """
    Helper function to turn in/out into src/dst pair

    Parameters
    ----------
    direction : {'in', 'out'}
        The direction to do conversion (direction relative to mongodb)

    Returns
    -------
    src, dst : str
        The source and destination strings in that order.
    """
    if direction == 'in':
        src, dst = '.', '[dot]'
    elif direction == 'out':
        src, dst = '[dot]', '.'
    else:
        raise ValueError('Only in/out allowed as direction params')

    return src, dst


def __replace_descriptor_data_key_dots(ev_desc, direction='in'):
    """Replace the '.' with [dot]
    I know the name is long. Bite me, it is private routine and I have an IDE

    Parameters
    ---------

    event_descriptor: metadataStore.database.event_descriptor.EventDescriptor
    EvenDescriptor instance

    direction: str
    If 'in' ->  replace . with [dot]
    If 'out' -> replace [dot] with .

    """
    src, dst = __src_dst(direction)
    ev_desc.data_keys = __replace_dict_keys(ev_desc.data_keys,
                                            src, dst)
    return ev_desc


def __replace_event_data_key_dots(event, direction='in'):
    """Replace the '.' with [dot]
    I know the name is long. Bite me, it is private routine and I have an IDE

    Parameters
    ---------

    event_descriptor: metadataStore.database.event_descriptor.EventDescriptor
    EvenDescriptor instance

    direction: str
    If 'in' ->  replace . with [dot]
    If 'out' -> replace [dot] with .

    """
    src, dst = __src_dst(direction)
    event.data = __replace_dict_keys(event.data,
                                     src, dst)
    return event
