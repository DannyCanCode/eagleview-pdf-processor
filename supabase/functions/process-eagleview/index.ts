import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req: Request) => {
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    // Get the file from the request
    const formData = await req.formData()
    const file = formData.get('file')
    
    if (!file) {
      throw new Error('No file provided')
    }

    // Get Python backend URL from environment variable
    const pythonBackendUrl = Deno.env.get('PYTHON_BACKEND_URL')
    if (!pythonBackendUrl) {
      throw new Error('Python backend URL not configured')
    }

    // Create Supabase client
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    // Upload file to Supabase Storage
    const timestamp = new Date().getTime()
    const fileName = `${timestamp}-${file.name}`
    const { data: storageData, error: storageError } = await supabaseClient
      .storage
      .from('eagleview-reports')
      .upload(fileName, file)

    if (storageError) {
      throw new Error(`Storage error: ${storageError.message}`)
    }

    // Get public URL for the uploaded file
    const { data: { publicUrl } } = supabaseClient
      .storage
      .from('eagleview-reports')
      .getPublicUrl(fileName)

    // Call Python backend to process the PDF
    const processingResponse = await fetch(`${pythonBackendUrl}/process-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        file_url: publicUrl,
        file_name: fileName
      })
    })

    if (!processingResponse.ok) {
      const error = await processingResponse.text()
      throw new Error(`Processing error: ${error}`)
    }

    const processingResult = await processingResponse.json()

    // Return the results
    return new Response(
      JSON.stringify({
        success: true,
        url: publicUrl,
        fileName: fileName,
        measurements: processingResult
      }),
      {
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      }
    )

  } catch (error) {
    console.error('Error:', error.message)
    return new Response(
      JSON.stringify({
        error: error.message,
        success: false
      }),
      {
        status: 500,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json',
        },
      }
    )
  }
}) 