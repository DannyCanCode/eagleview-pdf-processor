from pdf_processor.storage import AzureBlobStorage
import asyncio

async def test():
    storage = AzureBlobStorage()
    with open('test.pdf', 'rb') as f:
        url = await storage.upload_pdf(f.read(), 'test.pdf')
        print(f'Successfully uploaded to: {url}')

if __name__ == "__main__":
    asyncio.run(test()) 