import {
  Heading,
  Box,
  Card,
  CardBody,
  CardHeader,
  Flex,
  Center,
  Editable,
  EditableTextarea,
  IconButton,
  ListItem,
  Text,
  Tooltip,
  UnorderedList,
  VStack,
  HStack,
} from "@chakra-ui/react";
import { AddIcon, InfoIcon } from "@chakra-ui/icons";
import { GameDefinitionsService, Lore, AgentDef, Memory } from "client";
import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import DeleteModal from "util/DeleteModal";
import { ColoredPreview } from "util/ColoredPreview";

interface AgentLoreProps {
  agentUuid: string;
  agent: AgentDef;
  handleSave: (personalMemory: Memory[]) => Promise<void>;
}

export default function AgentLore(props: AgentLoreProps) {
  const params = useParams();
  const [sharedLore, setSharedLore] = useState<Lore[]>([]);
  const [personalMemory, setMemoryLore] = useState<Memory[]>([]);

  const handleDelete = (index: number) => {
    setMemoryLore(oldItems => {
      const newItems = [...oldItems];
      newItems.splice(index, 1);
      props.handleSave(newItems);
      return newItems;
    });
  };
  const handleClintIDChange = (index: number, newClientID: string) => {
    setMemoryLore(oldItems => {
      const newItems = [...oldItems];
      newItems[index].client_id = newClientID;
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
    setMemoryLore(oldItems => {
      const newItems = [...oldItems];
      newItems[index].description = newDescription;
      return newItems;
    });
  };

  useEffect(() => {
    const fetchData = async () => {
      const unfiltered = await GameDefinitionsService.getLore(params.gameUuid!);
      const filtered = unfiltered.filter(lore =>
        (lore.known_by ?? []).includes(props.agentUuid),
      );
      setSharedLore(filtered);
      const temp = props.agent.personal_lore ?? [];
      setMemoryLore(temp);
    };
    fetchData();
  }, [params.gameUuid, props.agentUuid, props.agent.personal_lore]);

  return (
    <VStack spacing={4} align={"left"}>
      <Heading size="lg">
        Shared Lore
        <Tooltip
          placement="top"
          label="These are defined in the game editing page."
        >
          <IconButton
            aria-label="Info"
            icon={<InfoIcon />}
            size="lg"
            variant="ghost"
          />
        </Tooltip>
      </Heading>
      {sharedLore.length === 0 && <Text size="lg">No Shared Lore</Text>}
      <UnorderedList>
        {sharedLore.map((lore, index) => (
          <ListItem key={index}>{lore.memory.description}</ListItem>
        ))}
      </UnorderedList>
      <Heading size="lg">Personal Lore</Heading>
      <Text>Personal memory: </Text>
      <Text>比如：塑造了角色的儿时噩梦.</Text>
      <Card
          onClick={() =>
            setMemoryLore(oldMemory => [
              { description: "Click to edit!", importance: 10  },
              ...oldMemory,
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
        {personalMemory.map((memory, index) => (
          <Card width={"100%"} key={index}>
            <CardBody>
              <Editable
                width={"full"}
                height="max-content"
                key={index}
                value={handleNullCheck(memory.client_id)}
                onChange={value => handleClintIDChange(index, value)}
                onSubmit={() => props.handleSave(personalMemory)}
              >
                <ColoredPreview minHeight={10} />
                <EditableTextarea value={memory.client_id} />
              </Editable>
              <HStack marginBottom={5}>
                <Editable
                  width={"full"}
                  height="max-content"
                  key={index}
                  value={memory.description}
                  onChange={value => handleDescriptionChange(index, value)}
                  onSubmit={() => props.handleSave(personalMemory)}
                >
                  <ColoredPreview minHeight={10} />
                  <EditableTextarea value={memory.description} />
                </Editable>
                <Box marginTop={"-8px"}>
                      <DeleteModal
                        text="Are you sure you want to delete this shared lore?"
                        onDelete={() => handleDelete(index)}
                      ></DeleteModal>
                </Box>
              </HStack>
            </CardBody>
          </Card>  
        ))}
    </VStack>
  );
}
