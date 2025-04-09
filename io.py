import os
from . import config
import scipy.io #temporal, bottom of file
from lxml import etree as eTree
import uuid
import time
from datetime import datetime, timedelta
from dateutil import parser as dateutil_parser

class Event():
    
    def __init__(self, kind, ch_id, ch_id_inv, begin, end):
        self._kind = kind
        self._ch_id = ch_id
        self._ch_id_inv = ch_id_inv
        self._begin = begin
        self._end = end

    def kind(self):
        return self._kind

    def ch_id(self):
        return self._ch_id

    def ch_id_inv(self):
        return self._ch_id_inv

    def begin(self):
        return self._begin

    def end(self):
        return self._end

#####################################

def _new_guid_string():
    return str(uuid.uuid4())

def _fix_format(aDateTime):
    #Format requiered by Micromed acording to documentation examples.
    return aDateTime.strftime('%Y-%m-%dT%H:%M:%S') + aDateTime.strftime('.%f')[:7] + 'Z'

def _define_hfo_type(parentElem, name, type_guid, description, text_color, graph_color):

    anHFOtype = eTree.SubElement(parentElem, "Definition", Name=name)
    
    eTree.SubElement(anHFOtype, "Guid").text = type_guid
    eTree.SubElement(anHFOtype, "Description").text = description
    eTree.SubElement(anHFOtype, "IsPredefined").text = "true"
    eTree.SubElement(anHFOtype, "IsDefinitionAdjustable").text = "false"
    eTree.SubElement(anHFOtype, "CanInsert").text = "true"
    eTree.SubElement(anHFOtype, "CanDelete").text = "true"
    eTree.SubElement(anHFOtype, "CanUpdateText").text = "true"
    eTree.SubElement(anHFOtype, "CanUpdatePosition").text = "true"
    eTree.SubElement(anHFOtype, "CanReassign").text = "false"
    eTree.SubElement(anHFOtype, "InsertionType").text = "ClickAndDrag"
    eTree.SubElement(anHFOtype, "FixedInsertionDuration").text = "PT1S"
    eTree.SubElement(anHFOtype, "TextType").text = "FromDefinitionDescription"
    eTree.SubElement(anHFOtype, "ReferenceType").text = "SingleLine"
    eTree.SubElement(anHFOtype, "DurationType").text = "Interval"
    eTree.SubElement(anHFOtype, "TextArgbColor").text = text_color
    eTree.SubElement(anHFOtype, "GraphicArgbColor").text = graph_color
    eTree.SubElement(anHFOtype, "GraphicType").text = "FillRectangle"
    eTree.SubElement(anHFOtype, "TextPositionType").text = "Top"
    eTree.SubElement(anHFOtype, "VisualizationType").text = "TextAndGraphic"
    eTree.SubElement(anHFOtype, "FontFamily").text = "Segoe UI"
    eTree.SubElement(anHFOtype, "FontSize").text = "11"
    eTree.SubElement(anHFOtype, "FontItalic").text = "false"
    eTree.SubElement(anHFOtype, "FontBold").text = "false"

def _build_tree():
    
    now = _fix_format(datetime.utcnow())  
    root = eTree.Element("EventFile", Version="1.00", 
                         CreationDate=now, Guid=_new_guid_string())
    evt_types = eTree.SubElement(root, "EventTypes")
    category = eTree.SubElement(evt_types, "Category", Name="HFO")
    
    eTree.SubElement(category, "Description").text = "HFO Category"
    eTree.SubElement(category, "IsPredefined").text = "true"
    eTree.SubElement(category, "Guid").text = config.HFO_CATEGORY_GUID
    hfoCategory = eTree.SubElement(category, "SubCategory", Name="HFO")
    
    eTree.SubElement(hfoCategory, "Description").text = "HFO Subcategory"
    eTree.SubElement(hfoCategory, "IsPredefined").text = "true"
    eTree.SubElement(hfoCategory, "Guid").text = config.HFO_SUBCATEGORY_GUID

    _define_hfo_type( parentElem=hfoCategory, name="HFO Spike", 
                      type_guid=config.DEF_HFO_SPIKE_GUID, 
                      description="HFO Spike Event Definition", 
                      text_color="4294901760", graph_color="805306623")


    _define_hfo_type( parentElem=hfoCategory, name="HFO Ripple", 
                      type_guid=config.DEF_HFO_RIPPLE_GUID,
                      description="HFO Ripple Event Definition",
                      text_color="4294901760", graph_color="822018048")

    _define_hfo_type( parentElem=hfoCategory, name="HFO FastRipple",
                      type_guid=config.DEF_HFO_FASTRIPPLE_GUID, 
                      description="HFO FastRipple Event Definition",
                      text_color="4294901760", graph_color="805371648")

    #Create Events label empty to append annotations later.
    events = eTree.SubElement(root, "Events")

    return eTree.ElementTree(root)

#Why some kinds are marked as spike and ripple or spike and fripple at the same time?.

class EventFile():

    def __init__(self, fname, rec_start_time=datetime.today(), tree=_build_tree(), events=set(), username='Username' ):
        self.fname = fname
        self.rec_start_time = rec_start_time
        self.tree = tree
        self.append_events(events, username)

    def rename(self, new_fname):
        self.fname = new_fname

    def set_rec_start_time(self, rec_start_time):
        self.rec_start_time = rec_start_time

    def change_tree(self, new_tree):
        self.tree = new_tree

    def name(self):
        return self.fname

    def events(self):
        eventsElem = self.tree.find('Events')
        xml_events = eventsElem.findall('Event')
        events = set()
        for event in xml_events:
            begin = dateutil_parser.parse( event.findtext('Begin') )
            end = dateutil_parser.parse( event.findtext('End') )
            ch_id = int( event.findtext('DerivationInvID') )
            ch_id_inv = int( event.findtext('DerivationNotInvID') )
            kind = config.event_kind_by_guid[ event.findtext('EventDefinitionGuid') ]
            events.add( Event(kind, ch_id, ch_id_inv, begin, end) )

        return events

    def append_events(self, events, username):
        for e in events:
            self.append_event(e, username)

    def append_event(self, anEvent, username):

        anEvent.kind()
        eventsElem = self.tree.getroot().find("Events")
        evt = eTree.SubElement(eventsElem, "Event", Guid=_new_guid_string() )
        now = _fix_format(datetime.utcnow())  
        
        eTree.SubElement(evt, "EventDefinitionGuid").text = config.event_guid_by_kind[ anEvent.kind() ]
        eTree.SubElement(evt, "Begin").text = anEvent.begin()
        eTree.SubElement(evt, "End").text = anEvent.end()
        eTree.SubElement(evt, "Value").text = "0"
        eTree.SubElement(evt, "ExtraValue").text = "0"
        eTree.SubElement(evt, "DerivationInvID").text = str( anEvent.ch_id() ) #Starting from 1. 
        eTree.SubElement(evt, "DerivationNotInvID").text = str( anEvent.ch_id_inv() ) 
        eTree.SubElement(evt, "CreatedBy").text = username
        eTree.SubElement(evt, "CreatedDate").text = now
        eTree.SubElement(evt, "UpdatedBy").text = username
        eTree.SubElement(evt, "UpdatedDate").text = now

    def save(self):
        write_evt(self)

####################################

def read_evt(evt_fname):
    parser = eTree.XMLParser(remove_blank_text=True)
    return EventFile(evt_fname, tree = eTree.parse(evt_fname, parser) )

def write_evt(evt_file):
    evt_file.tree.write(evt_file.name(), encoding="utf-8", xml_declaration=True, pretty_print=True)

def _add_events(events, matfile_vars, kind, subkinds, modified_chanlist, 
                original_chanlist, rec_start_time, on_offset, off_offset):
    for subkind in subkinds:
        channels = matfile_vars[subkind][0][0][0]
        if len(channels) > 0:
            for i in range(len(channels)):
                modified_channel_idx = channels[i][0] #index in modified_chanlist
                ch_name = modified_chanlist[0][modified_channel_idx - 1][0]
                ch_id = original_chanlist.index(ch_name) + 1 #assuming that start by 1 
                ch_id_inv = 0
                start_t = matfile_vars[subkind][0][0][6][i][0]
                finish_t = matfile_vars[subkind][0][0][7][i][0]
                begin = _fix_format(rec_start_time + timedelta(seconds=start_t)+on_offset)
                end = _fix_format(rec_start_time + timedelta(seconds=finish_t)+off_offset)

                events.add( Event(kind, ch_id, ch_id_inv, begin, end) )

def _add_events_bp(events, matfile_vars, kind, subkinds, modified_chanlist, #need to correct for new BP channels
                original_chanlist, bp_pairs, m2bp, rec_start_time, on_offset, off_offset):
    if m2bp is None:
        m2bp = {}  # Assign a default empty dictionary if m2bp is not passed
    for subkind in subkinds:
        channels = matfile_vars[subkind][0][0][0]
        if len(channels) > 0:
            for i in range(len(channels)):
                modified_channel_idx = channels[i][0] #index in modified_chanlist
                ch_name = modified_chanlist[0][modified_channel_idx - 1][0]
                ch_id = original_chanlist.index(ch_name) + 1 #assuming that start by 1
                if ch_name in m2bp:
                    ch_id_inv = 0
                else:
                    ch_id_inv = bp_pairs[ch_id-1] + 1 
                start_t = matfile_vars[subkind][0][0][6][i][0]
                finish_t = matfile_vars[subkind][0][0][7][i][0]
                begin = _fix_format(rec_start_time + timedelta(seconds=start_t)+on_offset)
                end = _fix_format(rec_start_time + timedelta(seconds=finish_t)+off_offset)

                events.add( Event(kind, ch_id, ch_id_inv, begin, end) )

# loads events from matlab structures and returns a set of Events
def load_events_from_matfiles(ez_top_out_dir, original_chanlist, bp_pairs, rec_start_time):
    events = set()
    for filename in os.listdir(ez_top_out_dir):
        if filename != '.keep':
            events_matfile = os.path.join(ez_top_out_dir, filename)  # Use os.path.join
            if '_mp_' in filename:  # Check filename, not full path
                chanlist_varname = 'monopolar_chanlist'
            elif '_bp_' in filename:
                chanlist_varname = 'bipolar_chanlist'
            else:
                print(f"Warning: Unknown file type: {filename}")
                continue  # Skip to the next file

            ripple_subkinds = ["RonO", "TRonS"]
            fripple_subkinds = ["ftRonO", "ftTRonS"]
            spike_subkinds = ["TRonS", "ftTRonS", "FRonS", "ftFRonS"]
            subkinds = ripple_subkinds + fripple_subkinds + spike_subkinds

            var_names = subkinds + [chanlist_varname, 'metadata']
            try:
                matfile_vars = scipy.io.loadmat(events_matfile, variable_names=var_names)
            except Exception as e:
                print(f"Error loading MAT file {filename}: {e}")
                continue

            if chanlist_varname not in matfile_vars or 'metadata' not in matfile_vars:
                print(f"Warning: Required variables not found in {filename}. Skipping.")
                continue

            modified_chanlist = matfile_vars[chanlist_varname]
            try:
                blocknum = int(matfile_vars['metadata']['file_block'][0][0])
            except (KeyError, TypeError, IndexError) as e:
                print(f"Warning: Error accessing file_block in {filename}: {e}. Assuming block 1.")
                blocknum = 1

            rec_start_time_adj = rec_start_time + timedelta(seconds=((blocknum - 1) * 600))
            m2bp = []

            if isinstance(chanlist_varname, str) and chanlist_varname == 'monopolar_chanlist':
                if 'hf_bad_m' in matfile_vars['metadata'] and isinstance(matfile_vars['metadata']['hf_bad_m'], np.ndarray) and matfile_vars['metadata']['hf_bad_m'].size > 0:
                    m2bp_1 = matfile_vars['metadata']['hf_bad_m'][0][0][0]
                    m2bp.extend(m2bp_1.tolist())
                else:
                    print(f"Warning: hf_bad_m not found or not in correct format in {filename}")

                if 'hf_bad_m2' in matfile_vars['metadata'] and isinstance(matfile_vars['metadata']['hf_bad_m2'], np.ndarray) and matfile_vars['metadata']['hf_bad_m2'].size > 0:
                    m2bp_2 = matfile_vars['metadata']['hf_bad_m2'][0][0][0]
                    m2bp.extend(m2bp_2.tolist())
                else:
                    print(f"Warning: hf_bad_m2 not found or not in correct format in {filename}")

                # Add events
                _add_events(events, matfile_vars, config.ripple_kind, ripple_subkinds,
                            modified_chanlist, original_chanlist, rec_start_time_adj,
                            config.ripple_on_offset, config.ripple_off_offset)

                _add_events(events, matfile_vars, config.fastRipple_kind, fripple_subkinds,
                            modified_chanlist, original_chanlist, rec_start_time_adj,
                            config.fripple_on_offset, config.fripple_off_offset)

                _add_events(events, matfile_vars, config.spike_kind, spike_subkinds,
                            modified_chanlist, original_chanlist, rec_start_time_adj,
                            config.spike_on_offset, config.spike_off_offset)
            else:  # Bipolar channel list
                _add_events_bp(events, matfile_vars, config.ripple_kind, ripple_subkinds,
                               modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj,
                               config.ripple_on_offset, config.ripple_off_offset)

                _add_events_bp(events, matfile_vars, config.fastRipple_kind, fripple_subkinds,
                               modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj,
                               config.fripple_on_offset, config.fripple_off_offset)

                _add_events_bp(events, matfile_vars, config.spike_kind, spike_subkinds,
                               modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj,
                               config.spike_on_offset, config.spike_off_offset)

            print(f"Finished processing {filename}, current total events: {len(events)}")

    print(f"\n✅ Event file processed. Total events loaded: {len(events)}")
    return events


# def load_events_from_matfiles(ez_top_out_dir, original_chanlist, bp_pairs, rec_start_time):
#     events = set()
#     for filename in os.listdir(ez_top_out_dir):
#         if filename != '.keep':
#             events_matfile = os.path.join(ez_top_out_dir, filename)  # Use os.path.join
#             if '_mp_' in filename:  # Check filename, not full path
#                 chanlist_varname = 'monopolar_chanlist'
#             elif '_bp_' in filename:
#                 chanlist_varname = 'bipolar_chanlist'
#             else:
#                 print(f"Warning: Unknown file type: {filename}")  # More informative message
#                 continue  # Skip to the next file

#             ripple_subkinds = ["RonO", "TRonS"]
#             fripple_subkinds = ["ftRonO", "ftTRonS"]
#             spike_subkinds = ["TRonS", "ftTRonS", "FRonS", "ftFRonS"]
#             subkinds = ripple_subkinds + fripple_subkinds + spike_subkinds

#             var_names = subkinds + [chanlist_varname, 'metadata'] # Correct way to create the list
#             try:
#                 matfile_vars = scipy.io.loadmat(events_matfile, variable_names=var_names)
#             except Exception as e:
#                 print(f"Error loading MAT file {filename}: {e}")
#                 continue # Skip to the next file

#             if chanlist_varname not in matfile_vars or 'metadata' not in matfile_vars:
#                 print(f"Warning: Required variables not found in {filename}. Skipping.")
#                 continue

#             modified_chanlist = matfile_vars[chanlist_varname]
#             try:
#                 blocknum = int(matfile_vars['metadata']['file_block'][0][0]) # Accessing file_block correctly
#             except (KeyError, TypeError, IndexError) as e:
#                 print(f"Warning: Error accessing file_block in {filename}: {e}. Assuming block 1.")
#                 blocknum = 1
#             rec_start_time_adj = rec_start_time + timedelta(seconds=((blocknum - 1) * 600))

#             m2bp = []  # Initialize m2bp outside the if block
#             if chanlist_varname == 'monopolar_chanlist':
#                 if 'hf_bad_m' in matfile_vars['metadata'] and isinstance(matfile_vars['metadata']['hf_bad_m'], np.ndarray) and matfile_vars['metadata']['hf_bad_m'].size > 0:
#                     m2bp_1 = matfile_vars['metadata']['hf_bad_m'][0][0][0] # Correct indexing
#                     m2bp.extend(m2bp_1.tolist()) # Extend the list using tolist()
#                 else:
#                     print(f"Warning: hf_bad_m not found or not in correct format in {filename}")

#                 if 'hf_bad_m2' in matfile_vars['metadata'] and isinstance(matfile_vars['metadata']['hf_bad_m2'], np.ndarray) and matfile_vars['metadata']['hf_bad_m2'].size > 0:
#                     m2bp_2 = matfile_vars['metadata']['hf_bad_m2'][0][0][0] # Correct indexing
#                     m2bp.extend(m2bp_2.tolist()) # Extend the list using tolist()
#                 else:
#                     print(f"Warning: hf_bad_m2 not found or not in correct format in {filename}")
#                     print(f"Event file is created successfully")

#                 _add_events(events, matfile_vars, config.ripple_kind, ripple_subkinds,
#                             modified_chanlist, original_chanlist, rec_start_time_adj,
#                             config.ripple_on_offset, config.ripple_off_offset)

#                 _add_events(events, matfile_vars, config.fastRipple_kind, fripple_subkinds,
#                             modified_chanlist, original_chanlist, rec_start_time_adj,
#                             config.fripple_on_offset, config.fripple_off_offset)

#                 _add_events(events, matfile_vars, config.spike_kind, spike_subkinds,
#                             modified_chanlist, original_chanlist, rec_start_time_adj,
#                             config.spike_on_offset, config.spike_off_offset)
#             else:  # Bipolar channel list
#                 _add_events_bp(events, matfile_vars, config.ripple_kind, ripple_subkinds,
#                                 modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj,
#                                 config.ripple_on_offset, config.ripple_off_offset)

#                 _add_events_bp(events, matfile_vars, config.fastRipple_kind, fripple_subkinds,
#                                 modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj,
#                                 config.fripple_on_offset, config.fripple_off_offset)

#                 _add_events_bp(events, matfile_vars, config.spike_kind, spike_subkinds,
#                                 modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj,
#                                 config.spike_on_offset, config.spike_off_offset)

#     return events


# def load_events_from_matfiles(ez_top_out_dir, original_chanlist, bp_pairs, rec_start_time):
#     events = set()
#     for filename in os.listdir(ez_top_out_dir):
#         if filename != '.keep':
#             events_matfile = ez_top_out_dir + filename
#             if '_mp_' in events_matfile:
#                 chanlist_varname = 'monopolar_chanlist'
#             elif '_bp_' in events_matfile:
#                 chanlist_varname = 'bipolar_chanlist'
#             else:
#                 print("Error in xml_writer xml_append_annotations") 
#             ripple_subkinds = ["RonO", "TRonS"]
#             fripple_subkinds = ["ftRonO", "ftTRonS"]
#             spike_subkinds = ["TRonS", "ftTRonS", "FRonS", "ftFRonS"]
#             subkinds =  ripple_subkinds + fripple_subkinds + spike_subkinds
#             var_names = subkinds.append(chanlist_varname)
#             matfile_vars = scipy.io.loadmat(events_matfile, variable_names=var_names)
#             modified_chanlist = matfile_vars[chanlist_varname] 
#             blocknum=int(matfile_vars['metadata']['file_block'])
#             rec_start_time_adj = (rec_start_time + timedelta(seconds=((blocknum-1)*600))) #v.0.0.1 adjust for file block fixed at 600 seconds
            
#             m2bp=[]

#             if chanlist_varname == 'monopolar_chanlist':
#                 m2bp_1=matfile_vars['metadata']['hf_bad_m']
#                 m2bp_2=matfile_vars['metadata']['hf_bad_m2']
                
#                 for x in range(len(m2bp_1[0][0][0])):
#                     m2bp.append(m2bp_1[0][0][0][x][0])
#                 for x in range(len(m2bp_2[0][0][0])):
#                     m2bp.append(m2bp_2[0][0][0][x][0])
               
#                 _add_events(events, matfile_vars, config.ripple_kind, ripple_subkinds, 
#                             modified_chanlist, original_chanlist, rec_start_time_adj, 
#                             config.ripple_on_offset, config.ripple_off_offset)
                
#                 _add_events(events, matfile_vars, config.fastRipple_kind, fripple_subkinds, 
#                             modified_chanlist, original_chanlist, rec_start_time_adj, 
#                             config.fripple_on_offset, config.fripple_off_offset)
                
#                 _add_events(events, matfile_vars, config.spike_kind, spike_subkinds, 
#                             modified_chanlist, original_chanlist, rec_start_time_adj, 
#                             config.spike_on_offset, config.spike_off_offset)
#             else:
#                 _add_events_bp(events, matfile_vars, config.ripple_kind, ripple_subkinds, 
#                             modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj, 
#                             config.ripple_on_offset, config.ripple_off_offset)
            
#                 _add_events_bp(events, matfile_vars, config.fastRipple_kind, fripple_subkinds, 
#                             modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj, 
#                             config.fripple_on_offset, config.fripple_off_offset)
            
#                 _add_events_bp(events, matfile_vars, config.spike_kind, spike_subkinds, 
#                             modified_chanlist, original_chanlist, bp_pairs, m2bp, rec_start_time_adj, 
#                             config.spike_on_offset, config.spike_off_offset)

#     return events


