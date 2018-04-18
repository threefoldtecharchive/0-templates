@0xf54d2ffc76b25226;

struct Schema {
    blockCreator @0: Text;             # reference to the block creator service
    blockCreatorIdentifier @1: Text;  # id representing the block creator upstream
    postUrlTemplate @2: Text;         # url template where to post the updates. eg http://127.0.0.1:4567/path/to/handler/{block_creator_identifier}/and/maybe/some/more/path
}
