import { useEffect, useState } from 'react'
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Spinner } from './ui/spinner'
import { toast } from "sonner"

type UploadStatus = "idle" | "uploading" | "success" | "error"

export function UploadSection() {
    const [file, setFile] = useState<File | null>(null);
    const [uploadStatus, setUploadStatus] = useState<UploadStatus>("idle");
    const [downloading, setDownloading] = useState<boolean>(true);
    const [documents, setDocuments] = useState<string[]>([]);

    useEffect(() => {
        getDocuments();
    }, []);

    async function getDocuments() {
        setDownloading(true);
        try {
            const url = "http://localhost:8000/documents";
            const response = await fetch(url);
            if (response.ok) {
                const docs = await response.json();
                setDocuments(docs);
                return;
            }
            toast.error("An error occurred while retrieving the documents.");
        } catch (error) {
            toast.error("An error occurred while retrieving the documents.");
            console.error(error);
        } finally {
            setDownloading(false);
        }
    }

    async function deleteDocument(fileName: string) {
        try {
            const url = "http://localhost:8000/document";
            const response = await fetch(`${url}?name=${encodeURIComponent(fileName)}`, {
                method: "DELETE"
            });
            if (response.ok) {
                setDocuments(prev => prev.filter(e => e !== fileName));
                toast.success(fileName + " sikeresen törölve")
                return;
            }
            toast.error("An error occurred while deleting the document: " + fileName);
        } catch (error) {
            toast.error("An error occurred while deleting the document: " + fileName);
            console.error(error);
        }
    }

    async function upload() {
        if (!file) return;
        setUploadStatus("uploading");
        const formData = new FormData();
        formData.append("file", file);
        try {
            const response = await fetch("http://localhost:8000/upload", {
                method: "POST",
                body: formData
            });
            if (response.ok) {
                toast.success("File sikeresen feltöltve!");
                setFile(null);
                setUploadStatus("idle");
                getDocuments();
                return;
            }
            setUploadStatus("error");
            toast.error("Hiba történt!");
        } catch {
            setUploadStatus("error");
            toast.error("Hiba történt!");
        }
    }

    return (
        <div className="flex flex-col gap-4">
            <label className={cn(
                "flex flex-col items-center justify-center w-full h-32 border-2 border-dashed border-gray-300 rounded-lg",
                uploadStatus !== "uploading" && "cursor-pointer hover:border-blue-400",
            )}>
                {uploadStatus === "uploading" && <Spinner className="size-8 text-blue-500" />}
                {uploadStatus !== "uploading" && <span>{file ? file.name : "Húzd ide a fájlt, vagy kattints"}</span>}
                <input type="file" className="hidden" disabled={uploadStatus === "uploading"} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
            </label>
            <div className="flex justify-end">
                <Button disabled={uploadStatus === "uploading"} onClick={upload}>Upload</Button>
            </div>

            {downloading && <Spinner className="size-5" />}
            {!downloading && documents.length === 0 && (
                <p className="text-sm text-gray-500">Nincs feltöltött dokumentum.</p>
            )}
            {!downloading && documents.length > 0 && (
                <ul className="flex flex-col gap-2">
                    {documents.map(doc => (
                        <li key={doc} className="flex justify-between items-center border rounded px-3 py-2 text-sm">
                            <span>{doc}</span>
                            <Button variant="destructive" size="sm" onClick={() => deleteDocument(doc)}>
                                Törlés
                            </Button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    )
}