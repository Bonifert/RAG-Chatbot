import {Tabs, TabsContent, TabsList, TabsTrigger} from "@/components/ui/tabs"
import { ChatSection } from './ChatSection'
import { UploadSection } from './UploadSection'
import { Card } from "./ui/card"

export default function ActionTab() {
  return (
    <Tabs defaultValue='chat' className="flex-1 min-h-0 flex flex-col">
        <TabsList>
            <TabsTrigger value='chat'>Ask</TabsTrigger>
            <TabsTrigger value='upload'>Upload document</TabsTrigger>
        </TabsList>
        <TabsContent value='chat' className="flex-1 min-h-0">
            <ChatSection/>
        </TabsContent >
        <TabsContent value='upload'>
            <Card className="w-100% p-3 shadow-sm">
                <UploadSection/>
            </Card>
        </TabsContent>
    </Tabs>
  )
}
