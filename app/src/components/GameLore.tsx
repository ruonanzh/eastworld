import { AgentDef, Lore } from "client";
import { Select } from "chakra-react-select";
import {
  Box,
  Card,
  CardBody,
  CardHeader,
  Center,
  Editable,
  EditableTextarea,
  Flex,
  Grid,
  HStack,
  Heading,
  IconButton,
  Tooltip,
  Tag,
  TagLabel,
  TagCloseButton,
  Input,
} from "@chakra-ui/react";
import { AddIcon, InfoIcon } from "@chakra-ui/icons";
import { useState, useEffect, useCallback } from "react";
import { ColoredPreview } from "util/ColoredPreview";
import DeleteModal from "util/DeleteModal";

interface GameLoreProps {
  existingLore: Lore[];
  agents: AgentDef[];
  handleSave: (sharedLore: Lore[]) => Promise<void>;
}

export default function GameLore(props: GameLoreProps) {
  const [sharedLore, setSharedLore] = useState<Lore[]>(props.existingLore);
  const [filteredAgents, setFilteredAgents] = useState<AgentDef[]>([]);
  const [loreIndicesToDisplay, setLoreIndicesToDisplay] = useState(
    new Set<number>(),
  );
  const [tempTagTexts, setTempTagTexts] = useState<string[]>([]);

  const agentUuidToName = (uuid: string) => {
    const agent = props.agents.find(a => a.uuid === uuid);
    return agent?.name ?? "";
  };

  const handleDelete = (index: number) => {
    setSharedLore(oldItems => {
      const newItems = [...oldItems];
      newItems.splice(index, 1);
      props.handleSave(newItems);
      return newItems;
    });
  };

  const handleClintIDChange = (index: number, newClientID: string) => {
    setSharedLore(oldItems => {
      const newItems = [...oldItems];
      newItems[index].memory.client_id = newClientID;
      return newItems;
    });
  }

  const handleNullCheck = (value: string | undefined) => {
    if (value === undefined || value === null) {
      return "";
    }
    return value;
  }

  const handleDescriptionChange = (index: number, newDescription: string) => {
    setSharedLore(oldItems => {
      const newItems = [...oldItems];
      newItems[index].memory.description = newDescription;
      return newItems;
    });
  };

  const handleKnownByChange = (index: number, uuids: string[]) => {
    setSharedLore(oldItems => {
      const newItems = [...oldItems];
      newItems[index].known_by = uuids;

      // This doesn't seem right, but I am not a frontend engineer.
      props.handleSave(newItems);
      return newItems;
    });
  };

  const handleFilterAgents = (uuids: string[]) => {
    const newFilteredAgents = props.agents.filter(agent =>
      uuids.includes(agent.uuid!),
    );

    setFilteredAgents(newFilteredAgents);
  };

  const handleAddTag = (index: number, tag: string) => {
    setSharedLore(oldItems => {
      const newItems = [...oldItems];
      if(newItems[index].memory.keywords === undefined || newItems[index].memory.keywords === null) {
        newItems[index].memory.keywords = [];
      }
      newItems[index].memory.keywords?.push(tag);
      
      props.handleSave(newItems);
      return newItems;
    });
  }

  const handleDeleteTag = (index: number, tagIndex: number) => {
    setSharedLore(oldItems => {
      const newItems = [...oldItems];
      newItems[index].memory.keywords?.splice(tagIndex, 1);

      props.handleSave(newItems);
      return newItems;
    });
  }
 

  const showSharedLore = useCallback((lore: Lore, agents: AgentDef[]) => {
    return agents
      .map(agent => agent.uuid)
      .every(element => lore.known_by?.includes(element!));
  }, []);

  useEffect(() => {
    const indexedLore = sharedLore.map((value, index) => ({ value, index }));
    const filteredLore = indexedLore.filter(item =>
      showSharedLore(item.value, filteredAgents),
    );
    const newIndicesSet: Set<number> = new Set();
    filteredLore.forEach(element => {
      newIndicesSet.add(element.index);
    });

    setLoreIndicesToDisplay(newIndicesSet);
  }, [showSharedLore, sharedLore, filteredAgents, tempTagTexts]);

  return (
    <>
      <Center margin={10}>
        <Heading size="xl">
          Shared Lore
          <Tooltip
            placement="top"
            label="Facts/events/background information about the world and the 
          story that multiple agents know. These are only included in 
          relevant interactions, so feel free to add as many as possible to 
          color in the world you're creating!"
          >
            <IconButton
              aria-label="Info"
              icon={<InfoIcon />}
              size="lg"
              variant="ghost"
            />
          </Tooltip>
        </Heading>
      </Center>
      <Center margin={10}>
        <Select
          placeholder="Known by ..."
          isMulti={true}
          size={"md"}
          colorScheme="purple"
          chakraStyles={{
            input: base => ({ ...base, width: "100%", minWidth: "100%" }),
            container: base => ({
              ...base,
              width: "100%",
              minWidth: "100%",
            }),
          }}
          value={filteredAgents.map(agent => ({
            value: agent.uuid!,
            label: agent.name,
          }))}
          options={props.agents.map(agent => ({
            value: agent.uuid!,
            label: agent.name,
          }))}
          onChange={agents =>
            handleFilterAgents(agents.map(agent => agent.value))
          }
          closeMenuOnSelect={false}
        ></Select>
      </Center>
      <Grid templateColumns="repeat(2, 1fr)" gap={8} marginBottom={100}>
        <Card
          onClick={() =>
            setSharedLore(oldLore => [
              { memory: { description: "Click to edit!", importance: 10 } },
              ...oldLore,
            ])
          }
          style={{ cursor: "pointer" }}
        >
          <CardBody>
            <Flex flexDirection="column" justify="center" h="100%">
              <CardHeader>
                <Center>
                  <Heading size="lg">
                    New Lore
                    <AddIcon marginLeft={3} />
                  </Heading>
                </Center>
              </CardHeader>
            </Flex>
          </CardBody>
        </Card>
        {sharedLore.map(
          (lore, index) =>
            loreIndicesToDisplay.has(index) && (
              <Card width={"100%"} key={index}>
                <CardBody>
                  <Editable
                      width={"full"}
                      height="max-content"
                      value={handleNullCheck(lore.memory.client_id)}
                      onChange = {value => handleClintIDChange(index, value)}
                      onSubmit={() => props.handleSave(sharedLore)}
                  >
                      <ColoredPreview minHeight={10} />
                      <EditableTextarea value={handleNullCheck(lore.memory.client_id)} />
                  </Editable>
                  <HStack marginBottom={5}>
                    <Editable
                      width={"full"}
                      height="max-content"
                      value={lore.memory.description}
                      onChange={value => handleDescriptionChange(index, value)}
                      onSubmit={() => props.handleSave(sharedLore)}
                    >
                      <ColoredPreview minHeight={10} />
                      <EditableTextarea value={lore.memory.description} />
                    </Editable>
                    <Box marginTop={"-8px"}>
                      <DeleteModal
                        text="Are you sure you want to delete this shared lore?"
                        onDelete={() => handleDelete(index)}
                      ></DeleteModal>
                    </Box>
                  </HStack>
                  <Select
                    placeholder="Known by ..."
                    isMulti={true}
                    size={"md"}
                    colorScheme="purple"
                    chakraStyles={{
                      input: base => ({
                        ...base,
                        width: "100%",
                        minWidth: "100%",
                      }),
                      container: base => ({
                        ...base,
                        width: "100%",
                        minWidth: "100%",
                      }),
                    }}
                    value={
                      lore.known_by
                        ? lore.known_by.map(uuid => ({
                            value: uuid,
                            label: agentUuidToName(uuid),
                          }))
                        : []
                    }
                    options={props.agents.map(agent => ({
                      value: agent.uuid!,
                      label: agent.name,
                    }))}
                    onChange={agents =>
                      handleKnownByChange(
                        index,
                        agents.map(agent => agent.value),
                      )
                    }
                    closeMenuOnSelect={false}
                  ></Select>
                  <HStack spacing={4} marginTop={5}>
                    {lore.memory.keywords?.map((keyword, keywordIndex) => (
                      <Tag key={keywordIndex} size="md" variant="solid" colorScheme="purple">
                        <TagLabel>{keyword}</TagLabel>
                        <TagCloseButton onClick={() => handleDeleteTag(index,keywordIndex)} />
                      </Tag>
                    ))}
                  </HStack>
                    
                  <Input marginTop={5} value ={tempTagTexts[index]} placeholder='Add Keyword' size='md' 
                      
                      onChange={ e => {
                        const newTempTagTexts = [...tempTagTexts];
                        newTempTagTexts[index] = e.target.value;
                        setTempTagTexts(newTempTagTexts);
                        }
                      }

                      onKeyDown={ e=> {
                        if(e.key === 'Enter') 
                        {
                          handleAddTag(index, tempTagTexts[index]);
                          tempTagTexts[index]='';
                        }
                      }
                  }/> 
                </CardBody>
              </Card>
            ),
        )}
      </Grid>
    </>
  );
}
