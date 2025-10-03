import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    Chip,
    ChipGroup,
    StatusMessage,
    ButtonGroup,
} from "@/components";
import { Button } from "@/components/ui/button";

interface EmailMethodCardProps {
    isCurrent: boolean;
    onSetup: () => void;
}

export function EmailMethodCard({ isCurrent, onSetup }: EmailMethodCardProps) {
    return (
        <Card className="border-2 border-gray-200">
            <CardHeader className="flex items-start gap-4 pb-0">
                <div className="text-3xl">📧</div>
                <div className="flex-1 space-y-2">
                    <CardTitle>Email Verification</CardTitle>
                    <CardDescription>Receive verification codes via email.</CardDescription>
                    <ChipGroup className="mb-1">
                        <Chip variant="primary">Simple</Chip>
                        <Chip variant="info">No Extra App Needed</Chip>
                    </ChipGroup>
                    {isCurrent && (
                        <StatusMessage variant="success" className="text-xs">
                            Current default method
                        </StatusMessage>
                    )}
                </div>
            </CardHeader>
            <CardContent className="pt-4">
                <ButtonGroup>
                    <Button onClick={onSetup} className="bg-blue-600 hover:bg-blue-700 text-white">
                        Setup
                    </Button>
                </ButtonGroup>
            </CardContent>
        </Card>
    );
}
