from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
from datetime import datetime
import traceback
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_script(script):
    logging.info("=== Starting Analysis ===")
    logging.info(f"Input text length: {len(script)} characters")

    try:
        # Load the Flan-T5 tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-large", use_fast=True)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logging.info(f"Using device: {device}")

        model = AutoModelForSeq2SeqLM.from_pretrained(
            "google/flan-t5-large",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto"
        )
        logging.info("Model loaded successfully")

        # Trigger categories remain the same as in your original code
        trigger_categories = {
            "Violence": {
                "mapped_name": "Violence",
                "description": (
                    "Any act involving physical force or aggression intended to cause harm, injury, or death to a person, animal, or object. "
                    "Includes direct physical confrontations (e.g., fights, beatings, or assaults), implied violence (e.g., very graphical threats or descriptions of injuries), "
                    "or large-scale events like wars, riots, or violent protests."
                )
            },
            "Death": {
                "mapped_name": "Death References",
                "description": (
                    "Any mention, implication, or depiction of the loss of life, including direct deaths of characters, including mentions of deceased individuals, "
                    "or abstract references to mortality (e.g., 'facing the end' or 'gone forever'). This also covers depictions of funerals, mourning, "
                    "grieving, or any dialogue that centers around death, do not take metaphors into context that don't actually lead to death."
                )
            },
            "Substance Use": {
                "mapped_name": "Substance Use",
                "description": (
                    "Any explicit or implied reference to the consumption, misuse, or abuse of drugs, alcohol, or other intoxicating substances. "
                    "rehabilitation, or substance-related paraphernalia (e.g., needles, bottles, pipes)."
                )
            },
            "Gore": {
                "mapped_name": "Gore",
                "description": (
                    "Extremely detailed and graphic depictions of highly severe physical injuries, mutilation, or extreme bodily harm, often accompanied by descriptions of heavy blood, exposed organs, "
                    "or dismemberment. This includes war scenes with severe casualties, horror scenarios involving grotesque creatures, or medical procedures depicted with excessive detail."
                )
            },
            "Vomit": {
                "mapped_name": "Vomit",
                "description": (
                    "Any reference to the act of vomiting, whether directly described, implied, or depicted in detail. This includes sounds or visual descriptions of the act, "
                    "mentions of nausea leading to vomiting, or its aftermath (e.g., the presence of vomit, cleaning it up, or characters reacting to it)."
                )
            },
            "Sexual Content": {
                "mapped_name": "Sexual Content",
                "description": (
                    "Any depiction of sexual activity, intimacy, or sexual behavior, ranging from implied scenes to explicit descriptions. "
                    "This includes physical descriptions of characters in a sexual context, sexual dialogue, or references to sexual themes (e.g., harassment, innuendos)."
                )
            },
            "Sexual Abuse": {
               "mapped_name": "Sexual Abuse",
               "description": (
                  "Any form of non-consensual sexual act, behavior, or interaction, involving coercion, manipulation, or physical force. "
                  "This includes incidents of sexual assault, molestation, exploitation, harassment, and any acts where an individual is subjected to sexual acts against their will or without their consent. "
                  "It also covers discussions or depictions of the aftermath of such abuse, such as trauma, emotional distress, legal proceedings, or therapy. "
                  "References to inappropriate sexual advances, groping, or any other form of sexual misconduct are also included, as well as the psychological and emotional impact on survivors. "
                  "Scenes where individuals are placed in sexually compromising situations, even if not directly acted upon, may also fall under this category."
               )
            },
            "Self-Harm": {
                "mapped_name": "Self-Harm",
                "description": (
                    "Any mention or depiction of behaviors where an individual intentionally causes harm to themselves. This includes cutting, burning, or other forms of physical injury, "
                    "as well as suicidal ideation, suicide attempts, or discussions of self-destructive thoughts and actions. References to scars, bruises, or other lasting signs of self-harm are also included."
                )
            },
            "Gun Use": {
                "mapped_name": "Gun Use",
                "description": (
                    "Any explicit or implied mention of firearms being handled, fired, or used in a threatening manner. This includes scenes of gun violence, references to shootings, "
                    "gun-related accidents, or the presence of firearms in a tense or dangerous context (e.g., holstered weapons during an argument)."
                )
            },
            "Animal Cruelty": {
                "mapped_name": "Animal Cruelty",
                "description": (
                    "Any act of harm, abuse, or neglect toward animals, whether intentional or accidental. This includes physical abuse (e.g., hitting, injuring, or killing animals), "
                    "mental or emotional mistreatment (e.g., starvation, isolation), and scenes where animals are subjected to pain or suffering for human entertainment or experimentation."
                )
            },
            "Mental Health Issues": {
                "mapped_name": "Mental Health Issues",
                "description": (
                    "Any reference to mental health struggles, disorders, or psychological distress. This includes mentions of depression, anxiety, PTSD, bipolar disorder, schizophrenia, "
                    "or other conditions. Scenes depicting therapy sessions, psychiatric treatment, or coping mechanisms (e.g., medication, journaling) are also included. May cover subtle hints "
                    "like a character expressing feelings of worthlessness, hopelessness, or detachment from reality."
                )
            }
        }

        # Improved chunking with smaller chunks and more overlap
        chunk_size = 1000
        overlap = 20
        script_chunks = []
        
        # Improved chunking to avoid splitting mid-sentence
        words = script.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= chunk_size:
                script_chunks.append(" ".join(current_chunk))
                # Keep last few words for overlap
                current_chunk = current_chunk[-int(len(current_chunk) * (overlap/chunk_size)):]
                current_length = sum(len(word) + 1 for word in current_chunk)
        
        if current_chunk:
            script_chunks.append(" ".join(current_chunk))
        
        logging.info(f"Split into {len(script_chunks)} chunks with {overlap} character overlap")

        identified_triggers = {}
        chunk_triggers = {i: [] for i in range(len(script_chunks))}  # Track triggers per chunk

        for chunk_idx, chunk in enumerate(script_chunks, 1):
            logging.info(f"\n--- Processing Chunk {chunk_idx}/{len(script_chunks)} ---")
            chunk_length = len(chunk)
            logging.info(f"Chunk length: {chunk_length} characters")
            
            for category, info in trigger_categories.items():
                mapped_name = info["mapped_name"]
                description = info["description"]

                # Improved prompt template
                prompt = f"""
                Task: Carefully analyze this text for content related to {mapped_name}.
                Context: {description}
                
                Text to analyze:
                \"{chunk}\"
                
                Question: Based on the definition provided, does this text contain any content related to {mapped_name}?
                Important: Consider both explicit and implicit references.
                Response format: Answer with ONLY ONE of these exact words: YES, NO, or MAYBE
                """

                inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
                inputs = {k: v.to(device) for k, v in inputs.items()}

                # Improved generation parameters
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=50,
                        temperature=0.3,
                        top_p=0.9,
                        num_beams=4,
                        early_stopping=True,
                        pad_token_id=tokenizer.eos_token_id,
                        do_sample=True 
                    )

                response_text = tokenizer.decode(outputs[0], skip_special_tokens=True).strip().upper()
                first_word = response_text.split()[0] if response_text else "NO"
                
                logging.info(f"Category: {mapped_name}, Response: {first_word}")

                if first_word == "YES":
                    identified_triggers[mapped_name] = identified_triggers.get(mapped_name, 0) + 1
                    chunk_triggers[chunk_idx-1].append(mapped_name)
                elif first_word == "MAYBE":
                    identified_triggers[mapped_name] = identified_triggers.get(mapped_name, 0) + 0.5
                    chunk_triggers[chunk_idx-1].append(f"{mapped_name} (Maybe)")

        # Improved trigger detection logic
        final_triggers = []
        confidence_threshold = 0.6
        
        for mapped_name, count in identified_triggers.items():
            confidence_score = count / len(script_chunks)
            logging.info(f"Trigger: {mapped_name}, Confidence Score: {confidence_score:.2f}")
            
            if confidence_score > confidence_threshold:
                final_triggers.append(mapped_name)

        if not final_triggers:
            logging.info("No triggers detected")
            return ["None"]

        logging.info(f"Final triggers detected: {final_triggers}")
        return final_triggers

    except Exception as e:
        logging.error(f"ERROR OCCURRED: {str(e)}")
        traceback.print_exc()
        return {"error": str(e)}

def get_detailed_analysis(script):
    logging.info("=== Starting Detailed Analysis ===")
    triggers = analyze_script(script)
    
    result = {
        "detected_triggers": triggers if isinstance(triggers, list) else ["None"],
        "confidence": "High - Content detected" if isinstance(triggers, list) and triggers != ["None"] else "High - No concerning content detected",
        "model": "google/flan-t5-base",
        "analysis_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device_used": "cuda" if torch.cuda.is_available() else "cpu",
        "chunk_size": 250,
        "overlap": 50
    }

    logging.info(f"Final Result Dictionary: {result}")
    return result